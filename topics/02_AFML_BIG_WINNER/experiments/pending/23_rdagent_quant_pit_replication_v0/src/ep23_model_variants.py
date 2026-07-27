"""Frozen model variants for EP23 23D1 controlled attribution."""

from __future__ import annotations

import torch
from torch import nn


class FlattenedWindowMLP(nn.Module):
    """Capacity-matched MLP over the complete flattened factor window."""

    def __init__(self, num_features: int, num_timesteps: int):
        super().__init__()
        self.network = nn.Sequential(
            nn.Flatten(),
            nn.Linear(num_features * num_timesteps, 352),
            nn.GELU(),
            nn.Dropout(0.10),
            nn.Linear(352, 64),
            nn.GELU(),
            nn.Dropout(0.10),
            nn.Linear(64, 1),
        )
        self._initialize_linear_layers()

    def _initialize_linear_layers(self) -> None:
        for layer in self.modules():
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.zeros_(layer.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


class LastStateGRU128(nn.Module):
    """Two-layer GRU using only its final normalized hidden state."""

    def __init__(self, num_features: int, num_timesteps: int):
        super().__init__()
        self.num_timesteps = num_timesteps
        self.gru = nn.GRU(
            input_size=num_features,
            hidden_size=128,
            num_layers=2,
            batch_first=True,
            dropout=0.15,
            bidirectional=False,
        )
        self.layer_norm = nn.LayerNorm(128)
        self.projection = nn.Linear(128, 64)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(0.10)
        self.output_head = nn.Linear(64, 1)
        self._initialize_linear_layers()

    def _initialize_linear_layers(self) -> None:
        for layer in (self.projection, self.output_head):
            nn.init.xavier_uniform_(layer.weight)
            nn.init.zeros_(layer.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        hidden_sequence, _ = self.gru(x)
        final_state = self.layer_norm(hidden_sequence[:, -1, :])
        projected = self.dropout(self.activation(self.projection(final_state)))
        return self.output_head(projected)


class AttentiveGRU128(nn.Module):
    """The 23D candidate architecture without its output-file side effect."""

    def __init__(self, num_features: int, num_timesteps: int):
        super().__init__()
        self.num_timesteps = num_timesteps
        self.gru = nn.GRU(
            input_size=num_features,
            hidden_size=128,
            num_layers=2,
            batch_first=True,
            dropout=0.15,
            bidirectional=False,
        )
        self.layer_norm = nn.LayerNorm(128)
        self.attention_projection = nn.Linear(128, 64)
        self.attention_score = nn.Linear(64, 1, bias=False)
        self.projection = nn.Linear(128, 64)
        self.activation = nn.GELU()
        self.dropout = nn.Dropout(0.10)
        self.output_head = nn.Linear(64, 1)
        self._initialize_linear_layers()

    def _initialize_linear_layers(self) -> None:
        for layer in (
            self.attention_projection,
            self.attention_score,
            self.projection,
            self.output_head,
        ):
            nn.init.xavier_uniform_(layer.weight)
            if layer.bias is not None:
                nn.init.zeros_(layer.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        hidden_sequence, _ = self.gru(x)
        normalized_hidden = self.layer_norm(hidden_sequence)
        attention_hidden = torch.tanh(
            self.attention_projection(normalized_hidden)
        )
        attention_logits = self.attention_score(attention_hidden)
        attention_weights = torch.softmax(attention_logits, dim=1)
        context = torch.sum(attention_weights * normalized_hidden, dim=1)
        projected = self.dropout(self.activation(self.projection(context)))
        return self.output_head(projected)


MODEL_VARIANTS = {
    "flattened_mlp": FlattenedWindowMLP,
    "last_state_gru": LastStateGRU128,
    "attentive_gru": AttentiveGRU128,
}
