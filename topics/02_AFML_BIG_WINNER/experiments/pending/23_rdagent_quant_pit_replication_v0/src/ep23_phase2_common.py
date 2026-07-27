"""Shared factor-library helpers for EP23 Phase 2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import qlib
import yaml
from qlib.contrib.data.loader import Alpha158DL, Alpha360DL
from qlib.data import D


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    )


def load_configs(phase2_config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    phase2 = yaml.safe_load(phase2_config_path.read_text(encoding="utf-8"))
    base_path = phase2_config_path.parent / phase2["base_config"]
    base = yaml.safe_load(base_path.read_text(encoding="utf-8"))
    return phase2, base


def normalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if list(frame.index.names) == ["instrument", "datetime"]:
        frame = frame.swaplevel()
    frame.index = frame.index.set_names(["datetime", "instrument"])
    return frame.sort_index()


def get_library_definitions(
    base_config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    alpha20 = dict(base_config["alpha20"])
    alpha158_exprs, alpha158_names = Alpha158DL.get_feature_config()
    alpha360_exprs, alpha360_names = Alpha360DL.get_feature_config()
    definitions = {
        "A20_RDAGENT_PINNED": {
            "source": "EP23 config.yaml alpha20 + RD-Agent ALPHA20",
            "names": list(alpha20),
            "expressions": list(alpha20.values()),
        },
        "A158_QLIB_PINNED": {
            "source": "qlib.contrib.data.loader.Alpha158DL.get_feature_config",
            "names": list(alpha158_names),
            "expressions": list(alpha158_exprs),
        },
        "A360_QLIB_PINNED": {
            "source": "qlib.contrib.data.loader.Alpha360DL.get_feature_config",
            "names": list(alpha360_names),
            "expressions": list(alpha360_exprs),
        },
    }
    for source_id, adaptation_id in [
        (
            "A158_QLIB_PINNED",
            "A157_QLIB_NO_VWAP_REGISTERED_ADAPTATION",
        ),
        (
            "A360_QLIB_PINNED",
            "A300_QLIB_NO_VWAP_REGISTERED_ADAPTATION",
        ),
    ]:
        source = definitions[source_id]
        retained = [
            (name, expression)
            for name, expression in zip(
                source["names"], source["expressions"], strict=True
            )
            if "VWAP" not in name.upper() and "$vwap" not in expression.lower()
        ]
        definitions[adaptation_id] = {
            "source": (
                f"{source['source']}; registered no-VWAP adaptation because "
                "the PIT provider has no audited $vwap field"
            ),
            "names": [name for name, _ in retained],
            "expressions": [expression for _, expression in retained],
        }
    return definitions


def library_as_dict(library: dict[str, Any]) -> dict[str, str]:
    return dict(zip(library["names"], library["expressions"], strict=True))


def library_hashes(library: dict[str, Any]) -> dict[str, str]:
    names = list(library["names"])
    expressions = list(library["expressions"])
    pairs = list(zip(names, expressions, strict=True))
    return {
        "names_sha256": canonical_json_sha256(names),
        "expressions_sha256": canonical_json_sha256(expressions),
        "ordered_pairs_sha256": canonical_json_sha256(pairs),
    }


def init_qlib(provider_path: Path) -> None:
    qlib.init(provider_uri=str(provider_path), region="cn")


def materialize_library(
    *,
    provider_path: Path,
    market: str,
    library: dict[str, Any],
    labels: dict[str, str],
    start_time: str,
    end_time: str,
) -> pd.DataFrame:
    init_qlib(provider_path)
    expressions = [*library["expressions"], *labels.values()]
    columns = [*library["names"], *labels.keys()]
    frame = D.features(
        D.instruments(market),
        expressions,
        start_time=start_time,
        end_time=end_time,
        freq="day",
    )
    frame = normalize_feature_frame(frame)
    frame.columns = columns
    return frame.replace([np.inf, -np.inf], np.nan)


def materialization_summary(
    library_id: str, frame: pd.DataFrame, feature_names: list[str]
) -> dict[str, Any]:
    feature_frame = frame[feature_names]
    dates = frame.index.get_level_values("datetime")
    instruments = frame.index.get_level_values("instrument")
    per_feature_finite = feature_frame.notna().mean(axis=0)
    per_feature_nunique = feature_frame.nunique(dropna=True)
    return {
        "library_id": library_id,
        "feature_count": len(feature_names),
        "rows": int(len(frame)),
        "dates": int(dates.nunique()),
        "instruments": int(instruments.nunique()),
        "date_start": pd.Timestamp(dates.min()).date().isoformat(),
        "date_end": pd.Timestamp(dates.max()).date().isoformat(),
        "finite_ratio": float(feature_frame.notna().to_numpy().mean()),
        "minimum_feature_finite_ratio": float(per_feature_finite.min()),
        "median_feature_finite_ratio": float(per_feature_finite.median()),
        "constant_or_empty_features": int((per_feature_nunique <= 1).sum()),
        "unique_index": bool(frame.index.is_unique),
    }
