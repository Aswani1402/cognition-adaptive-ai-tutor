import os
import json
import math
import random
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader


DATA_PATH = os.path.join("external", "dataset", "assistments.csv")
OUT_DIR = os.path.join("external", "models", "dkt", "skillbuilder_v1")
ENCODING = "latin1"

# Training params (you can tune for accuracy)
MAX_SEQ_LEN = 100
BATCH_SIZE = 64
EPOCHS = 5
LR = 1e-3
EMBED_DIM = 64
HIDDEN_DIM = 128
VAL_SPLIT = 0.15
SEED = 42


def set_seed(seed: int):
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def build_id_maps(df: pd.DataFrame) -> Tuple[Dict[str, int], Dict[str, int]]:
    users = sorted(df["user_id"].astype(str).unique().tolist())
    skills = sorted(df["skill_id"].astype(str).unique().tolist())

    user2idx = {u: i for i, u in enumerate(users)}
    # reserve 0 for PAD
    skill2idx = {s: i + 1 for i, s in enumerate(skills)}

    return user2idx, skill2idx


def make_sequences(df: pd.DataFrame, skill2idx: Dict[str, int]) -> List[Tuple[List[int], List[int]]]:
    """
    Returns list of (skill_seq, correct_seq) per user.
    """
    seqs = []
    for uid, g in df.groupby("user_id", sort=False):
        g = g.sort_values("order_id")
        skills = g["skill_id"].astype(str).tolist()
        correct = g["correct"].astype(int).clip(0, 1).tolist()

        s_idx = [skill2idx[s] for s in skills if s in skill2idx]
        c_idx = correct[: len(s_idx)]

        if len(s_idx) < 2:
            continue

        # chunk long sequences
        for i in range(0, len(s_idx), MAX_SEQ_LEN):
            chunk_s = s_idx[i : i + MAX_SEQ_LEN]
            chunk_c = c_idx[i : i + MAX_SEQ_LEN]
            if len(chunk_s) >= 2:
                seqs.append((chunk_s, chunk_c))

    return seqs


class DKTDataset(Dataset):
    def __init__(self, seqs: List[Tuple[List[int], List[int]]], pad_id: int = 0):
        self.seqs = seqs
        self.pad_id = pad_id

    def __len__(self):
        return len(self.seqs)

    def __getitem__(self, idx: int):
        skills, correct = self.seqs[idx]
        # build x as (skill, correct) interaction embedding index
        # simplest: x_skill and x_correct separate
        return torch.tensor(skills, dtype=torch.long), torch.tensor(correct, dtype=torch.float32)


def collate_fn(batch):
    skills, correct = zip(*batch)
    lengths = [len(s) for s in skills]
    max_len = max(lengths)

    skill_pad = torch.zeros(len(batch), max_len, dtype=torch.long)
    corr_pad = torch.zeros(len(batch), max_len, dtype=torch.float32)
    mask = torch.zeros(len(batch), max_len, dtype=torch.bool)

    for i, (s, c) in enumerate(zip(skills, correct)):
        L = len(s)
        skill_pad[i, :L] = s
        corr_pad[i, :L] = c
        mask[i, :L] = True

    return skill_pad, corr_pad, mask


class DKTModel(nn.Module):
    def __init__(self, num_skills: int, embed_dim: int, hidden_dim: int):
        super().__init__()
        # num_skills includes PAD=0
        self.skill_emb = nn.Embedding(num_skills, embed_dim, padding_idx=0)
        self.correct_emb = nn.Embedding(2, embed_dim)  # 0/1
        self.rnn = nn.LSTM(input_size=embed_dim * 2, hidden_size=hidden_dim, batch_first=True)
        self.out = nn.Linear(hidden_dim, num_skills)  # predict prob for each skill

    def forward(self, skill_seq, corr_seq):
        # corr_seq float -> long 0/1
        corr_long = corr_seq.long().clamp(0, 1)
        se = self.skill_emb(skill_seq)
        ce = self.correct_emb(corr_long)
        x = torch.cat([se, ce], dim=-1)
        h, _ = self.rnn(x)
        logits = self.out(h)  # (B, T, num_skills)
        return logits


def compute_metrics(preds: List[float], labels: List[int]) -> Dict[str, float]:
    # simple accuracy + logloss (AUC later if you want)
    eps = 1e-7
    pred_bin = [1 if p >= 0.5 else 0 for p in preds]
    acc = sum(int(p == y) for p, y in zip(pred_bin, labels)) / max(1, len(labels))

    # logloss
    ll = 0.0
    for p, y in zip(preds, labels):
        p = min(max(p, eps), 1 - eps)
        ll += -(y * math.log(p) + (1 - y) * math.log(1 - p))
    ll = ll / max(1, len(labels))
    return {"accuracy": acc, "logloss": ll}


def main():
    set_seed(SEED)
    os.makedirs(OUT_DIR, exist_ok=True)

    # load minimal columns only (fast + safe)
    df = pd.read_csv(
        DATA_PATH,
        encoding=ENCODING,
        usecols=["order_id", "user_id", "skill_id", "correct"],
        low_memory=False,
    )

    # clean
    df = df.dropna(subset=["order_id", "user_id", "skill_id", "correct"])
    df["order_id"] = pd.to_numeric(df["order_id"], errors="coerce")
    df["correct"] = pd.to_numeric(df["correct"], errors="coerce")
    df = df.dropna(subset=["order_id", "correct"])
    df["correct"] = df["correct"].astype(int).clip(0, 1)

    user2idx, skill2idx = build_id_maps(df)

    seqs = make_sequences(df, skill2idx)
    random.shuffle(seqs)

    n_val = int(len(seqs) * VAL_SPLIT)
    val_seqs = seqs[:n_val]
    train_seqs = seqs[n_val:]

    num_skills = max(skill2idx.values()) + 1  # +1 because pad=0

    train_ds = DKTDataset(train_seqs)
    val_ds = DKTDataset(val_seqs)

    train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, collate_fn=collate_fn)
    val_dl = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, collate_fn=collate_fn)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DKTModel(num_skills=num_skills, embed_dim=EMBED_DIM, hidden_dim=HIDDEN_DIM).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.BCEWithLogitsLoss()

    best_val = 1e9
    for ep in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        steps = 0

        for skill_seq, corr_seq, mask in train_dl:
            skill_seq = skill_seq.to(device)
            corr_seq = corr_seq.to(device)
            mask = mask.to(device)

            logits = model(skill_seq, corr_seq)  # (B,T,num_skills)

            # Predict next-step correctness for the NEXT skill
            target_skill = skill_seq[:, 1:]
            target_correct = corr_seq[:, 1:]
            pred_logits = logits[:, :-1, :]  # align
            # gather predictions for next skill
            gathered = torch.gather(pred_logits, 2, target_skill.unsqueeze(-1)).squeeze(-1)

            valid_mask = mask[:, 1:]
            loss = loss_fn(gathered[valid_mask], target_correct[valid_mask])

            opt.zero_grad()
            loss.backward()
            opt.step()

            total_loss += float(loss.item())
            steps += 1

        avg_loss = total_loss / max(1, steps)

        # val
        model.eval()
        v_preds, v_labels = [], []
        v_loss = 0.0
        v_steps = 0

        with torch.no_grad():
            for skill_seq, corr_seq, mask in val_dl:
                skill_seq = skill_seq.to(device)
                corr_seq = corr_seq.to(device)
                mask = mask.to(device)

                logits = model(skill_seq, corr_seq)

                target_skill = skill_seq[:, 1:]
                target_correct = corr_seq[:, 1:]
                pred_logits = logits[:, :-1, :]
                gathered = torch.gather(pred_logits, 2, target_skill.unsqueeze(-1)).squeeze(-1)

                valid_mask = mask[:, 1:]
                loss = loss_fn(gathered[valid_mask], target_correct[valid_mask])

                v_loss += float(loss.item())
                v_steps += 1

                probs = torch.sigmoid(gathered[valid_mask]).detach().cpu().numpy().tolist()
                labs = target_correct[valid_mask].detach().cpu().numpy().astype(int).tolist()
                v_preds.extend(probs)
                v_labels.extend(labs)

        avg_vloss = v_loss / max(1, v_steps)
        metrics = compute_metrics(v_preds, v_labels)

        print(f"epoch={ep} train_loss={avg_loss:.4f} val_loss={avg_vloss:.4f} acc={metrics['accuracy']:.4f} logloss={metrics['logloss']:.4f}")

        if avg_vloss < best_val:
            best_val = avg_vloss
            torch.save(model.state_dict(), os.path.join(OUT_DIR, "model.pt"))
            with open(os.path.join(OUT_DIR, "id_map.json"), "w", encoding="utf-8") as f:
                json.dump({"skill2idx": skill2idx}, f, indent=2)

    print("Saved best model to:", OUT_DIR)


if __name__ == "__main__":
    main()