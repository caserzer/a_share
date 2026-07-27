from pathlib import Path

import torch
from torch import nn


class CompactAttentiveGRU128(nn.Module):
    """Two-layer GRU with additive temporal attention for return prediction."""

    def __init__(self, num_features: int, num_timesteps: int):
        super().__init__()
        self.num_features = num_features
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
        self.dropout = nn.Dropout(p=0.10)
        self.output_head = nn.Linear(64, 1)

        self._initialize_linear_layers()

    def _initialize_linear_layers(self) -> None:
        linear_layers = (
            self.attention_projection,
            self.attention_score,
            self.projection,
            self.output_head,
        )
        for layer in linear_layers:
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
        projected = self.projection(context)
        projected = self.activation(projected)
        projected = self.dropout(projected)
        output = self.output_head(projected)

        output_path = Path(__file__).resolve().with_name("output.pth")
        torch.save(output.detach().cpu(), output_path)
        return output


model_cls = CompactAttentiveGRU128
