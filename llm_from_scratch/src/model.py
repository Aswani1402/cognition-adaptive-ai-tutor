import math
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class CogniTutorLMConfig:
    vocab_size: int = 8000
    context_length: int = 256
    n_layers: int = 4
    n_heads: int = 4
    n_embd: int = 256
    dropout: float = 0.1


class CausalSelfAttention(nn.Module):
    def __init__(self, config: CogniTutorLMConfig):
        super().__init__()

        assert config.n_embd % config.n_heads == 0

        self.n_heads = config.n_heads
        self.head_dim = config.n_embd // config.n_heads

        self.qkv_proj = nn.Linear(config.n_embd, 3 * config.n_embd)
        self.out_proj = nn.Linear(config.n_embd, config.n_embd)

        self.attn_dropout = nn.Dropout(config.dropout)
        self.resid_dropout = nn.Dropout(config.dropout)

        mask = torch.tril(torch.ones(config.context_length, config.context_length))
        self.register_buffer(
            "causal_mask",
            mask.view(1, 1, config.context_length, config.context_length),
        )

    def forward(self, x):
        batch_size, seq_len, embd_dim = x.shape

        qkv = self.qkv_proj(x)
        q, k, v = qkv.split(embd_dim, dim=2)

        q = q.view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        k = k.view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        v = v.view(batch_size, seq_len, self.n_heads, self.head_dim).transpose(1, 2)

        attn_scores = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)

        causal_mask = self.causal_mask[:, :, :seq_len, :seq_len]
        attn_scores = attn_scores.masked_fill(causal_mask == 0, float("-inf"))

        attn_weights = F.softmax(attn_scores, dim=-1)
        attn_weights = self.attn_dropout(attn_weights)

        out = attn_weights @ v
        out = out.transpose(1, 2).contiguous().view(batch_size, seq_len, embd_dim)

        out = self.out_proj(out)
        out = self.resid_dropout(out)

        return out


class MLP(nn.Module):
    def __init__(self, config: CogniTutorLMConfig):
        super().__init__()

        self.net = nn.Sequential(
            nn.Linear(config.n_embd, 4 * config.n_embd),
            nn.GELU(),
            nn.Linear(4 * config.n_embd, config.n_embd),
            nn.Dropout(config.dropout),
        )

    def forward(self, x):
        return self.net(x)


class TransformerBlock(nn.Module):
    def __init__(self, config: CogniTutorLMConfig):
        super().__init__()

        self.ln_1 = nn.LayerNorm(config.n_embd)
        self.attn = CausalSelfAttention(config)

        self.ln_2 = nn.LayerNorm(config.n_embd)
        self.mlp = MLP(config)

    def forward(self, x):
        x = x + self.attn(self.ln_1(x))
        x = x + self.mlp(self.ln_2(x))
        return x


class CogniTutorLM(nn.Module):
    def __init__(self, config: CogniTutorLMConfig):
        super().__init__()

        self.config = config

        self.token_embedding = nn.Embedding(config.vocab_size, config.n_embd)
        self.position_embedding = nn.Embedding(config.context_length, config.n_embd)

        self.dropout = nn.Dropout(config.dropout)

        self.blocks = nn.ModuleList(
            [TransformerBlock(config) for _ in range(config.n_layers)]
        )

        self.ln_f = nn.LayerNorm(config.n_embd)
        self.lm_head = nn.Linear(config.n_embd, config.vocab_size, bias=False)

        # Weight tying: common GPT trick.
        self.lm_head.weight = self.token_embedding.weight

        self.apply(self._init_weights)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)

        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, input_ids, target_ids=None):
        batch_size, seq_len = input_ids.shape

        if seq_len > self.config.context_length:
            raise ValueError(
                f"Sequence length {seq_len} exceeds context length {self.config.context_length}"
            )

        positions = torch.arange(0, seq_len, device=input_ids.device).unsqueeze(0)

        tok_emb = self.token_embedding(input_ids)
        pos_emb = self.position_embedding(positions)

        x = self.dropout(tok_emb + pos_emb)

        for block in self.blocks:
            x = block(x)

        x = self.ln_f(x)
        logits = self.lm_head(x)

        loss = None

        if target_ids is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)),
                target_ids.view(-1),
                ignore_index=0,  # pad_id
            )

        return logits, loss

    def count_parameters(self):
        return sum(p.numel() for p in self.parameters())


if __name__ == "__main__":
    config = CogniTutorLMConfig(
        vocab_size=8000,
        context_length=256,
        n_layers=4,
        n_heads=4,
        n_embd=256,
        dropout=0.1,
    )

    model = CogniTutorLM(config)

    dummy_input = torch.randint(0, config.vocab_size, (4, 256))
    dummy_target = torch.randint(0, config.vocab_size, (4, 256))

    logits, loss = model(dummy_input, dummy_target)

    print("Model test successful.")
    print(f"Parameters: {model.count_parameters():,}")
    print(f"Input shape: {dummy_input.shape}")
    print(f"Logits shape: {logits.shape}")
    print(f"Loss: {loss.item():.4f}")