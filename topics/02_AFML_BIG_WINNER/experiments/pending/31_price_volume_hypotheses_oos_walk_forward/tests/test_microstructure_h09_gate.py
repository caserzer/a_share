from ep30_adapter import h09_gate


def test_daily_turnover_is_not_trade_size():
    assert h09_gate(["volume", "turnover_rate", "money", "open", "close"]) == "BLOCKED_DATA"


def test_microstructure_requires_timestamp_attestation():
    cols = ["trade_count", "trade_size", "known_at", "trade_category"]
    assert h09_gate(cols) == "BLOCKED_DATA"
    assert h09_gate(cols, timestamp_attested=True) == "ELIGIBLE"
