from dataclasses import asdict, dataclass
from pathlib import Path

from src.cognitutor_lm_config import ROOT


@dataclass
class ModelFirstTrainingConfig:
    seed: int = 42
    train_path: Path = ROOT / "training_data" / "model_first_full" / "tutor_train.jsonl"
    val_path: Path = ROOT / "training_data" / "model_first_full" / "tutor_val.jsonl"
    test_path: Path = ROOT / "training_data" / "model_first_full" / "tutor_test.jsonl"
    output_dir: Path = ROOT / "models" / "cognitutor_lm_model_first_full"
    checkpoints_dir: Path = ROOT / "models" / "cognitutor_lm_model_first_full" / "checkpoints"
    best_model_path: Path = ROOT / "models" / "cognitutor_lm_model_first_full" / "best_model.pt"
    batch_size: int = 8
    learning_rate: float = 3e-5
    weight_decay: float = 0.01
    max_epochs: int = 1
    max_additional_round_epochs: int = 1
    early_stopping_patience: int = 2
    grad_clip: float = 1.0
    max_val_batches: int = 40
    local_only: bool = True
    no_pretrained_models: bool = True

    def to_jsonable(self):
        data = asdict(self)
        return {k: str(v) if isinstance(v, Path) else v for k, v in data.items()}


CONFIG = ModelFirstTrainingConfig()
