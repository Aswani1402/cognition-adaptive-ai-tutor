from __future__ import annotations

import torch
import torch.nn as nn


class DKTModel(nn.Module):
    def __init__(self, num_skills: int, embed_dim: int = 32, hidden_dim: int = 64):
        super().__init__()
        self.skill_emb = nn.Embedding(num_skills, embed_dim, padding_idx=0)
        self.correct_emb = nn.Embedding(2, embed_dim)
        self.rnn = nn.LSTM(
            input_size=embed_dim * 2,
            hidden_size=hidden_dim,
            batch_first=True,
        )
        self.out = nn.Linear(hidden_dim, num_skills)

    def forward(self, skill_seq: torch.Tensor, corr_seq: torch.Tensor) -> torch.Tensor:
        corr_long = corr_seq.long().clamp(0, 1)
        skill_emb = self.skill_emb(skill_seq)
        correct_emb = self.correct_emb(corr_long)
        x = torch.cat([skill_emb, correct_emb], dim=-1)
        h, _ = self.rnn(x)
        return self.out(h)
