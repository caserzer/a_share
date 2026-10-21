"""Explicit execution, cash/rights and unknown outcomes; no adjusted-price shortcut."""

from dataclasses import dataclass, asdict
from decimal import Decimal
import math
import pandas as pd
from pit import Calendar, stamp


@dataclass(frozen=True)
class Label:
    security_id: str
    origin: str
    horizon: str
    return_policy: str
    status: str
    reason: str
    entry: str | None = None
    target: str | None = None
    exit: str | None = None
    value: float | None = None
    loss_below_minus20: bool | None = None
    mfe: float | None = None
    mae: float | None = None
    mature_at: str | None = None
    quality_tier: str = "UNKNOWN/BLOCKED"

    def to_dict(self):
        return asdict(self)


class LabelBuilder:
    def __init__(self, calendar: Calendar, bars, actions=None, coverage=None):
        self.calendar = calendar
        self.bars = bars.copy()
        if not self.bars.empty:
            self.bars["date"] = pd.to_datetime(self.bars.date).dt.normalize()
            if self.bars.duplicated(["security_id", "date"]).any():
                raise ValueError(
                    "conflicting bars require explicit resolution before labeling"
                )
        self.actions = actions.copy() if actions is not None else pd.DataFrame()
        self.coverage = coverage.copy() if coverage is not None else pd.DataFrame()

    def price_and_corporate_action_path(self, security, start, end, policy):
        if policy not in ("price", "total", "executable"):
            raise ValueError("unknown return policy")
        bars = self.bars[self.bars.security_id.eq(security)].copy()
        bars = bars[
            bars.date.between(
                pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
            )
        ]
        actions = self.actions
        if not actions.empty:
            actions = actions[actions.security_id.eq(security)].copy()
            actions = actions[
                pd.to_datetime(actions.effective_date).between(start, end)
            ]
        return {
            "bars": bars.sort_values("date"),
            "actions": actions,
            "policy": policy,
            "rights_coverage_verified": self._covered(security, start, end),
        }

    def _covered(self, security, start, end):
        f = self.coverage
        if f.empty:
            return False
        f = f[f.security_id.eq(security)]
        return any(
            bool(r.complete)
            and bool(r.source_sha256)
            and pd.Timestamp(r.start) <= pd.Timestamp(start)
            and pd.Timestamp(r.end) >= pd.Timestamp(end)
            for r in f.itertuples()
        )

    def _nav(self, security, entry, end, mark, policy, paid_through=None):
        """Gross one-share position. Cash held, no reinvestment; receivable only in total."""
        shares, cash, receivable = 1.0, 0.0, 0.0
        f = self.actions
        if f.empty:
            return mark, None
        f = f[f.security_id.eq(security)].copy()
        f["effective_date"] = pd.to_datetime(f.effective_date)
        f = f[(f.effective_date > entry) & (f.effective_date <= end)].sort_values(
            "effective_date"
        )
        # A dividend's record date may precede another share change. Entitlements use
        # actual position at record close, not the later payment-date position.
        holdings = [(entry, 1.0)]
        for r in f.itertuples():
            if not bool(r.verified) or not r.source_sha256:
                return None, "UNVERIFIED_CORPORATE_ACTION"
            record = pd.Timestamp(r.record_date)
            if pd.isna(record):
                return None, "MISSING_ENTITLEMENT_DATE"
            if record < entry:
                continue
            if record >= r.effective_date:
                return None, "INVALID_RECORD_EX_DATE_ORDER"
            position = next((n for d, n in reversed(holdings) if d <= record), 0)
            if r.kind == "cash_dividend":
                amount = position * float(r.cash_per_share)
                pay = pd.Timestamp(r.payment_date)
                if not math.isfinite(amount) or amount < 0 or pd.isna(pay):
                    return None, "MISSING_CASH_PAYMENT_EVIDENCE"
                if pay <= (paid_through if paid_through is not None else end):
                    cash += amount
                else:
                    receivable += amount
            elif r.kind == "split":
                ratio = float(r.share_multiplier)
                if not math.isfinite(ratio) or ratio <= 0:
                    return None, "INVALID_SHARE_MULTIPLIER"
                delivery = pd.Timestamp(r.payment_date)
                if pd.isna(delivery) or delivery > end:
                    return None, "UNDELIVERED_SHARE_RIGHTS"
                shares += position * (ratio - 1)
                holdings.append((r.effective_date, shares))
            else:
                return None, "COMPLEX_RIGHTS_REQUIRE_POSITION_LEDGER"
        if policy == "executable" and receivable:
            return None, "CASH_NOT_YET_PAID_AT_EXIT"
        return shares * mark + cash + (receivable if policy == "total" else 0), None

    @staticmethod
    def _flag(value):
        if pd.isna(value):
            return None
        if value is True or value == 1:
            return True
        if value is False or value == 0:
            return False
        raise ValueError("execution flag must be boolean or null")

    def build_labels(
        self,
        security,
        origin,
        horizon,
        return_policy="total",
        asof_time=None,
        cost_bps=None,
    ):
        if return_policy not in ("price", "total", "executable"):
            raise ValueError("unsupported policy")
        decision = stamp(origin)
        day = decision.tz_localize(None).normalize()
        days = self.calendar.days
        cutoff = (
            stamp(asof_time)
            if asof_time is not None
            else stamp(self.calendar.verified_through + pd.Timedelta(hours=15))
        )
        visible_day = min(
            cutoff.tz_localize(None).normalize(), self.calendar.verified_through
        )
        base = dict(
            security_id=security,
            origin=str(decision),
            horizon=str(horizon),
            return_policy=return_policy,
        )

        def result(status, reason, **kwargs):
            return Label(**base, status=status, reason=reason, **kwargs)

        if day not in days:
            return result("UNKNOWN", "ORIGIN_NOT_VERIFIED_SESSION")
        if decision < stamp(day + pd.Timedelta(hours=15)):
            return result("UNKNOWN", "CONTRACT_REQUIRES_AFTER_CLOSE_DECISION")
        if horizon == "6_calendar_months":
            target_i = days.searchsorted(day + pd.DateOffset(months=6))
        elif isinstance(horizon, int) and horizon in (20, 60, 120):
            target_i = days.get_loc(day) + horizon
        else:
            raise ValueError("horizon must be 6_calendar_months or 20/60/120 sessions")
        if target_i >= len(days):
            return result("CENSORED", "TARGET_BEYOND_VERIFIED_CALENDAR")
        target = days[target_i]
        if target > visible_day:
            return result("CENSORED", "HORIZON_NOT_MATURE", target=str(target.date()))
        f = self.bars[self.bars.security_id.eq(security)].set_index("date").sort_index()
        entry = exit_day = None
        for date in days[(days > day) & (days <= visible_day)]:
            if stamp(date + pd.Timedelta(hours=9, minutes=30)) > cutoff:
                break
            if date not in f.index:
                return result(
                    "UNKNOWN",
                    "MISSING_EXECUTION_STATUS_OR_SOURCE",
                    target=str(target.date()),
                )
            flag = self._flag(f.loc[date].get("can_buy"))
            if flag is None:
                return result(
                    "UNKNOWN", "UNKNOWN_BUY_EXECUTION", target=str(target.date())
                )
            if flag:
                entry = date
                break
        if entry is None:
            return result("UNKNOWN", "NO_FILLED_ENTRY", target=str(target.date()))
        info = dict(entry=str(entry.date()), target=str(target.date()))
        # Do not allow a blocked entry after the target to create a shorter label.
        if entry >= target:
            return result("UNKNOWN", "ENTRY_NOT_BEFORE_TARGET", **info)
        for date in days[(days >= target) & (days > entry) & (days <= visible_day)]:
            if stamp(date + pd.Timedelta(hours=9, minutes=30)) > cutoff:
                break
            if date not in f.index:
                return result("UNKNOWN", "MISSING_EXIT_SOURCE_OR_STATUS", **info)
            flag = self._flag(f.loc[date].get("can_sell"))
            if flag is None:
                return result("UNKNOWN", "UNKNOWN_SELL_EXECUTION", **info)
            if flag:
                exit_day = date
                break
        if exit_day is None:
            return result(
                "UNKNOWN", "NO_EXECUTABLE_EXIT_TERMINAL_RIGHTS_UNVERIFIED", **info
            )
        info.update(
            exit=str(exit_day.date()),
            mature_at=str(stamp(exit_day + pd.Timedelta(hours=9, minutes=30))),
        )
        path = f.reindex(days[(days >= entry) & (days <= target)])
        entry_price = f.loc[entry].get("open")
        exit_price = f.loc[exit_day].get("open")
        if (
            pd.isna(entry_price)
            or entry_price <= 0
            or pd.isna(exit_price)
            or exit_price <= 0
        ):
            return result("UNKNOWN", "MISSING_RAW_OPEN", **info)
        if return_policy != "price" and not self._covered(security, entry, exit_day):
            return result("UNKNOWN", "INCOMPLETE_ACTION_AND_SETTLEMENT_LEDGER", **info)
        if return_policy == "executable" and cost_bps is None:
            return result("UNKNOWN", "EXECUTION_COST_POLICY_NOT_SPECIFIED", **info)
        if cost_bps is not None and (not math.isfinite(cost_bps) or cost_bps < 0):
            raise ValueError("invalid explicit round-trip cost")
        if return_policy == "price":
            terminal = exit_price
        else:
            terminal, reason = self._nav(
                security,
                entry,
                exit_day,
                exit_price,
                return_policy,
                paid_through=visible_day
                if cutoff.hour >= 15
                else visible_day - pd.Timedelta(days=1),
            )
            if reason == "CASH_NOT_YET_PAID_AT_EXIT" and return_policy == "executable":
                info["mature_at"] = None
                return result("CENSORED", "CASH_SETTLEMENT_NOT_OBSERVED", **info)
            if reason:
                return result("UNKNOWN", reason, **info)
            if return_policy == "executable" and not self.actions.empty:
                cash = self.actions[
                    self.actions.security_id.eq(security)
                    & self.actions.kind.eq("cash_dividend")
                ]
                cash = cash[
                    (pd.to_datetime(cash.effective_date) > entry)
                    & (pd.to_datetime(cash.effective_date) <= exit_day)
                    & (pd.to_datetime(cash.record_date) >= entry)
                ]
                if not cash.empty:
                    paid_at = pd.to_datetime(cash.payment_date).max() + pd.Timedelta(
                        hours=15
                    )
                    info["mature_at"] = str(
                        max(stamp(info["mature_at"]), stamp(paid_at))
                    )
        marks = []
        for date, row in path.iterrows():
            close = row.get("close")
            if pd.isna(close) or close <= 0:
                # A dated suspension can explain a missing quote; never infer suspension.
                if row.get("missing_reason") == "SUSPENDED" and marks:
                    close = float(path.loc[:date, "close"].ffill().iloc[-1])
                else:
                    return result("UNKNOWN", "INCOMPLETE_MFE_MAE_PRICE_PATH", **info)
            # A target-open exit excludes target close from the held path.
            if date >= exit_day:
                break
            # Interim marks include earned receivables; only terminal executable
            # cash requires actual payment. An earlier payment wait is not a failed exit.
            nav, reason = (
                (close, None)
                if return_policy == "price"
                else self._nav(security, entry, date, close, "total")
            )
            if reason:
                return result("UNKNOWN", reason, **info)
            marks.append(nav / entry_price - 1)
        decimal_value = Decimal(str(terminal)) / Decimal(str(entry_price)) - 1
        if return_policy == "executable":
            decimal_value -= Decimal(str(cost_bps)) / 10000
        value = float(decimal_value)
        marks = [0.0, *marks, value]
        return result(
            "KNOWN",
            "RAW_PRICE_ONLY_NOT_TOTAL_RETURN" if return_policy == "price" else "OK",
            value=float(value),
            loss_below_minus20=bool(decimal_value < Decimal("-0.2")),
            mfe=float(max(marks)),
            mae=float(min(marks)),
            quality_tier="Historical-proxy",
            **info,
        )


def missing_price_reason(
    date, listing_date, delist_date=None, suspended=None, source_failed=False
):
    date = pd.Timestamp(date).normalize()
    if date < pd.Timestamp(listing_date):
        return "NOT_LISTED"
    if (
        delist_date is not None
        and not pd.isna(delist_date)
        and date >= pd.Timestamp(delist_date)
    ):
        return "DELISTED"
    if suspended is True:
        return "SUSPENDED"
    return "SOURCE_FAILURE" if source_failed else "UNKNOWN"
