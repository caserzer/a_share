from __future__ import annotations

import sys
from pathlib import Path

import torch

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from ep23_model_variants import MODEL_VARIANTS  # noqa: E402


def test_model_variants_share_the_frozen_interface() -> None:
    inputs = torch.zeros(4, 20, 20)
    for model_class in MODEL_VARIANTS.values():
        model = model_class(num_features=20, num_timesteps=20)
        assert model(inputs).shape == (4, 1)


def test_capacity_matching_and_attention_increment() -> None:
    parameter_counts = {
        name: sum(parameter.numel() for parameter in model_class(20, 20).parameters())
        for name, model_class in MODEL_VARIANTS.items()
    }
    assert parameter_counts == {
        "flattened_mlp": 163809,
        "last_state_gru": 165249,
        "attentive_gru": 173569,
    }
    assert parameter_counts["attentive_gru"] > parameter_counts["last_state_gru"]
