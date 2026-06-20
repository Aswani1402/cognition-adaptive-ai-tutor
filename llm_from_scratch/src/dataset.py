import json
import random
from pathlib import Path
from typing import Dict, List, Tuple

import torch
from torch.utils.data import Dataset, DataLoader

from src.tokenizer_wrapper import CogniTutorTokenizer


ROOT_DIR = Path(__file__).resolve().parents[1]

DATASET_PATH = ROOT_DIR / "data" / "processed" / "tutor_instruction_dataset.jsonl"

SPLIT_DIR = ROOT_DIR / "data" / "splits"
TRAIN_PATH = SPLIT_DIR / "train.jsonl"
VAL_PATH = SPLIT_DIR / "val.jsonl"
TEST_PATH = SPLIT_DIR / "test.jsonl"


def load_jsonl(path: Path) -> List[Dict]:
    rows = []

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    return rows


def save_jsonl(rows: List[Dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def create_splits(
    dataset_path: Path = DATASET_PATH,
    train_ratio: float = 0.90,
    val_ratio: float = 0.05,
    seed: int = 42,
):
    rows = load_jsonl(dataset_path)

    random.seed(seed)
    random.shuffle(rows)

    total = len(rows)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)

    train_rows = rows[:train_end]
    val_rows = rows[train_end:val_end]
    test_rows = rows[val_end:]

    save_jsonl(train_rows, TRAIN_PATH)
    save_jsonl(val_rows, VAL_PATH)
    save_jsonl(test_rows, TEST_PATH)

    print("Splits created successfully.")
    print(f"Total rows: {total}")
    print(f"Train: {len(train_rows)} -> {TRAIN_PATH}")
    print(f"Val: {len(val_rows)} -> {VAL_PATH}")
    print(f"Test: {len(test_rows)} -> {TEST_PATH}")


class TutorLMDataset(Dataset):
    def __init__(
        self,
        path: Path,
        tokenizer: CogniTutorTokenizer,
        context_length: int = 256,
    ):
        self.rows = load_jsonl(path)
        self.tokenizer = tokenizer
        self.context_length = context_length
        self.pad_id = tokenizer.pad_id

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows[idx]
        text = row.get("training_text", "")

        token_ids = self.tokenizer.encode(text, add_bos=False, add_eos=False)

        # Truncate to context_length + 1 because input and target are shifted.
        token_ids = token_ids[: self.context_length + 1]

        # Pad if too short.
        if len(token_ids) < self.context_length + 1:
            token_ids = token_ids + [self.pad_id] * ((self.context_length + 1) - len(token_ids))

        input_ids = token_ids[:-1]
        target_ids = token_ids[1:]

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "target_ids": torch.tensor(target_ids, dtype=torch.long),
        }


def create_dataloaders(
    batch_size: int = 4,
    context_length: int = 256,
    num_workers: int = 0,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    tokenizer = CogniTutorTokenizer()

    if not TRAIN_PATH.exists() or not VAL_PATH.exists() or not TEST_PATH.exists():
        create_splits()

    train_dataset = TutorLMDataset(TRAIN_PATH, tokenizer, context_length)
    val_dataset = TutorLMDataset(VAL_PATH, tokenizer, context_length)
    test_dataset = TutorLMDataset(TEST_PATH, tokenizer, context_length)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )

    return train_loader, val_loader, test_loader


if __name__ == "__main__":
    create_splits()

    train_loader, val_loader, test_loader = create_dataloaders(
        batch_size=4,
        context_length=256,
    )

    batch = next(iter(train_loader))

    print("\nDataset loader test successful.")
    print(f"Train batches: {len(train_loader)}")
    print(f"Val batches: {len(val_loader)}")
    print(f"Test batches: {len(test_loader)}")
    print(f"input_ids shape: {batch['input_ids'].shape}")
    print(f"target_ids shape: {batch['target_ids'].shape}")