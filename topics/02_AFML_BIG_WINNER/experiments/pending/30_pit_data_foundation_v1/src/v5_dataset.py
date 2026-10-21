"""Verified reader for v5 inferred qfq labels, separate from frozen strict v4."""
import json
from pathlib import Path

import pandas as pd

from archive import sha
from v5_core import PUBLIC
from v5_labels import HORIZONS, POLICIES


class D2PriceInferenceDataset:
    def __init__(self, release=None):
        if release is None:
            release = json.loads((PUBLIC / "release.json").read_text())["path"]
        self.root = Path(release)
        complete = json.loads((self.root / "COMPLETE.json").read_text())
        if sha(self.root / "FULL_MANIFEST.json") != complete["full_manifest_sha256"]:
            raise ValueError("changed v5 manifest")
        self.files = {r["relative_path"]: r["sha256"] for r in json.loads((self.root / "FULL_MANIFEST.json").read_text())}
        self.inventory = self._read("inputs/normalized/securities.parquet")
        self.continuous = self._read("inputs/normalized/code_intervals.parquet")
        self.bse = self._read("inputs/inputs/baseline/normalized/code_intervals.parquet")

    def _read(self, name):
        p = self.root / name
        if name not in self.files or not p.exists() or sha(p) != self.files[name]:
            raise ValueError("changed or missing v5 data: " + name)
        return pd.read_parquet(p)

    def _sid(self, security):
        if security in set(self.inventory.security_id):
            return security
        values = set(self.inventory.loc[self.inventory.instrument.eq(security) | self.inventory.metadata_instrument_v3.eq(security), "security_id"])
        values.update(self.continuous.loc[self.continuous.instrument.eq(security), "security_id"])
        values.update(self.bse.loc[self.bse.historical_instrument.eq(security), "security_id"])
        if len(values) != 1:
            raise KeyError("unknown or ambiguous identity: " + str(security))
        return next(iter(values))

    def build_labels(self, security, origin, horizon=20, return_policy="price", quality_tier="Historical-proxy", asof_time=None):
        if return_policy not in POLICIES:
            raise ValueError("unsupported requested policy")
        if quality_tier != "Historical-proxy":
            return dict(value=None, status="UNKNOWN", reason="V5_PRICE_INFERENCE_IS_HISTORICAL_PROXY", quality_tier="Historical-proxy")
        if isinstance(horizon, int):
            horizon = "6_calendar_months" if horizon == 6 else f"{horizon}_sessions"
        if horizon not in HORIZONS:
            raise ValueError("unsupported horizon")
        sid = self._sid(security)
        f = self._read(f"normalized/labels/{horizon}_{return_policy}.parquet")
        day = pd.Timestamp(origin)
        if day.tzinfo is not None:
            day = day.tz_convert("Asia/Shanghai").tz_localize(None)
        day = day.normalize()
        f = f[f.security_id.eq(sid) & f.date.eq(day)]
        if len(f) != 1:
            return dict(value=None, status="UNKNOWN", reason="NO_CANDIDATE_MONTH_ORIGIN", quality_tier="Historical-proxy")
        row = f.iloc[0]
        if asof_time is not None:
            cutoff = pd.Timestamp(asof_time)
            if cutoff.tzinfo is not None:
                cutoff = cutoff.tz_convert("Asia/Shanghai").tz_localize(None)
            needed = [pd.Timestamp(row[field]) + pd.Timedelta(hours=9, minutes=30)
                      for field in ["target_session", "entry_date", "exit_date"] if pd.notna(row.get(field))]
            if pd.notna(row.get("mature_at")):
                needed.append(pd.Timestamp(row.mature_at))
            if needed and max(needed) > cutoff:
                return dict(value=None, status="CENSORED", reason="INFERRED_LABEL_NOT_YET_MATURE_AT_ASOF", quality_tier="Historical-proxy")
        return {k: (None if pd.isna(v) else v) for k, v in f.iloc[0].to_dict().items()}

    def price_and_corporate_action_path(self, security, start, end, policy="qfq"):
        if policy != "qfq":
            raise ValueError("v5 reader provides inferred qfq path only")
        f = self._read(f"normalized/prices_qfq/{self._sid(security)}.parquet")
        f = f[f.date.between(pd.Timestamp(start), pd.Timestamp(end))].copy()
        for col in ["open", "high", "low", "close"]:
            f["raw_" + col] = f[col]
            f[col] = f["qfq_" + col]
        f.attrs.update(quality_tier="Historical-proxy", corporate_action_ledger_verified=False,
                       standard_ohlc_basis="qfq", raw_ohlc_columns="raw_open/raw_high/raw_low/raw_close",
                       method="unadjusted_OHLC_divided_by_Sina_qfq_divisor")
        return f

    def monthly_bridge(self):
        return self._read("normalized/full_monthly_bridge.parquet")
