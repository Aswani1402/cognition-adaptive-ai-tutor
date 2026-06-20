from __future__ import annotations

import torch
import torch.nn as nn


class SAKTModel(nn.Module):
    def __init__(
        self,
        num_concepts: int,
        embed_dim: int = 64,
        num_heads: int = 2,
        max_seq_len: int = 50,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.num_concepts = num_concepts
        self.max_seq_len = max_seq_len
        self.interaction_emb = nn.Embedding(num_concepts * 2, embed_dim, padding_idx=0)
        self.query_emb = nn.Embedding(num_concepts, embed_dim, padding_idx=0)
        self.pos_emb = nn.Embedding(max_seq_len, embed_dim)
        self.attn = nn.MultiheadAttention(embed_dim=embed_dim, num_heads=num_heads, dropout=dropout, batch_first=True)
        self.ffn = nn.Sequential(
            nn.Linear(embed_dim, embed_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(embed_dim, 1),
        )

    def forward(self, concept_seq: torch.Tensor, correct_seq: torch.Tensor) -> torch.Tensor:
        seq_len = concept_seq.shape[1]
        positions = torch.arange(seq_len, device=concept_seq.device).unsqueeze(0).expand_as(concept_seq)
        interaction_ids = concept_seq.long() + self.num_concepts * correct_seq.long().clamp(0, 1)
        interaction_ids = interaction_ids.clamp(0, self.num_concepts * 2 - 1)
        keys = self.interaction_emb(interaction_ids) + self.pos_emb(positions.clamp(max=self.max_seq_len - 1))
        queries = self.query_emb(concept_seq.long().clamp(0, self.num_concepts - 1))
        causal_mask = torch.triu(torch.ones(seq_len, seq_len, device=concept_seq.device, dtype=torch.bool), diagonal=1)
        attended, _ = self.attn(queries, keys, keys, attn_mask=causal_mask)
        return self.ffn(attended).squeeze(-1)
