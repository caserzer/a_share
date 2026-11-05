import json

from common import EXPECTED_RELEASE, frozen, OUT


def test_exact_frozen_configuration_and_release():
    assert len(frozen()["files"]) == 5
    receipt = json.loads((OUT / "audits/ep30_release_verification.json").read_text())
    assert receipt["release_id"] == EXPECTED_RELEASE
    assert receipt["files_verified"] == 35170


def test_policy_aliases_not_independent_samples():
    from common import config
    assert config("feature_label_contract")["labels"]["price_total_executable"] == "one_alias_only_price"
