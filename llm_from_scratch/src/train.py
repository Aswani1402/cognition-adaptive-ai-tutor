import argparse
import json
import math
import time
from pathlib import Path

import torch
import yaml
from torch.optim import AdamW
from tqdm import tqdm

from src.dataset import create_dataloaders
from src.model import CogniTutorLM, CogniTutorLMConfig


ROOT_DIR = Path(__file__).resolve().parents[1]


def get_device(device_name: str):
    if device_name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device_name)


def load_config(config_path: Path):
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_jsonl(row, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


@torch.no_grad()
def evaluate(model, val_loader, device, max_batches=100):
    model.eval()

    losses = []

    for batch_idx, batch in enumerate(val_loader):
        if batch_idx >= max_batches:
            break

        input_ids = batch["input_ids"].to(device)
        target_ids = batch["target_ids"].to(device)

        _, loss = model(input_ids, target_ids)
        losses.append(loss.item())

    model.train()

    if not losses:
        return None

    avg_loss = sum(losses) / len(losses)
    perplexity = math.exp(avg_loss) if avg_loss < 20 else float("inf")

    return {
        "val_loss": avg_loss,
        "perplexity": perplexity,
    }


def save_checkpoint(model, optimizer, config, epoch, step, val_metrics, checkpoint_path: Path):
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "config": config,
            "epoch": epoch,
            "step": step,
            "val_metrics": val_metrics,
        },
        checkpoint_path,
    )


def train(config_path: Path):
    config = load_config(config_path)

    model_cfg = config["model"]
    train_cfg = config["training"]
    output_cfg = config["outputs"]

    device = get_device(train_cfg.get("device", "auto"))

    print(f"Using device: {device}")

    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    lm_config = CogniTutorLMConfig(
        vocab_size=model_cfg["vocab_size"],
        context_length=model_cfg["context_length"],
        n_layers=model_cfg["n_layers"],
        n_heads=model_cfg["n_heads"],
        n_embd=model_cfg["n_embd"],
        dropout=model_cfg["dropout"],
    )

    train_loader, val_loader, _ = create_dataloaders(
        batch_size=train_cfg["batch_size"],
        context_length=model_cfg["context_length"],
        num_workers=0,
    )

    model = CogniTutorLM(lm_config).to(device)

    print(f"Model: {model_cfg['model_name']}")
    print(f"Parameters: {model.count_parameters():,}")
    print(f"Train batches: {len(train_loader)}")
    print(f"Val batches: {len(val_loader)}")

    optimizer = AdamW(
        model.parameters(),
        lr=float(train_cfg["learning_rate"]),
        weight_decay=float(train_cfg.get("weight_decay", 0.01)),
    )

    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")

    epochs = int(train_cfg["epochs"])
    grad_accum_steps = int(train_cfg.get("gradient_accumulation_steps", 1))
    grad_clip = float(train_cfg.get("grad_clip", 1.0))

    checkpoint_dir = ROOT_DIR / output_cfg["checkpoint_dir"]
    metrics_dir = ROOT_DIR / output_cfg["metrics_dir"]

    best_val_loss = float("inf")
    global_step = 0

    metrics_path = metrics_dir / "train_log.jsonl"

    if metrics_path.exists():
        metrics_path.unlink()

    print("\nStarting training...\n")

    for epoch in range(1, epochs + 1):
        model.train()

        running_loss = 0.0
        start_time = time.time()

        progress = tqdm(train_loader, desc=f"Epoch {epoch}/{epochs}")

        optimizer.zero_grad(set_to_none=True)

        for batch_idx, batch in enumerate(progress, start=1):
            input_ids = batch["input_ids"].to(device)
            target_ids = batch["target_ids"].to(device)

            with torch.amp.autocast("cuda", enabled=device.type == "cuda"):
                _, loss = model(input_ids, target_ids)
                loss = loss / grad_accum_steps

            scaler.scale(loss).backward()

            if batch_idx % grad_accum_steps == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)

                scaler.step(optimizer)
                scaler.update()

                optimizer.zero_grad(set_to_none=True)
                global_step += 1

            batch_loss = loss.item() * grad_accum_steps
            running_loss += batch_loss

            avg_train_loss = running_loss / batch_idx

            progress.set_postfix(
                {
                    "loss": f"{avg_train_loss:.4f}",
                    "step": global_step,
                }
            )

            # Quick validation every 1000 optimizer steps
            if global_step > 0 and global_step % 1000 == 0 and batch_idx % grad_accum_steps == 0:
                val_metrics = evaluate(model, val_loader, device, max_batches=100)

                log_row = {
                    "epoch": epoch,
                    "global_step": global_step,
                    "train_loss": avg_train_loss,
                    "val_loss": val_metrics["val_loss"],
                    "perplexity": val_metrics["perplexity"],
                    "time_sec": round(time.time() - start_time, 2),
                }

                save_jsonl(log_row, metrics_path)

                print(
                    f"\nStep {global_step} | "
                    f"train_loss={avg_train_loss:.4f} | "
                    f"val_loss={val_metrics['val_loss']:.4f} | "
                    f"ppl={val_metrics['perplexity']:.2f}\n"
                )

                if val_metrics["val_loss"] < best_val_loss:
                    best_val_loss = val_metrics["val_loss"]

                    best_path = checkpoint_dir / "cognitutor_s_best.pt"
                    save_checkpoint(
                        model=model,
                        optimizer=optimizer,
                        config=config,
                        epoch=epoch,
                        step=global_step,
                        val_metrics=val_metrics,
                        checkpoint_path=best_path,
                    )

                    print(f"Saved best checkpoint: {best_path}")

        # End-of-epoch validation
        val_metrics = evaluate(model, val_loader, device, max_batches=200)

        epoch_train_loss = running_loss / len(train_loader)

        log_row = {
            "epoch": epoch,
            "global_step": global_step,
            "train_loss": epoch_train_loss,
            "val_loss": val_metrics["val_loss"],
            "perplexity": val_metrics["perplexity"],
            "time_sec": round(time.time() - start_time, 2),
        }

        save_jsonl(log_row, metrics_path)

        print(
            f"\nEpoch {epoch} complete | "
            f"train_loss={epoch_train_loss:.4f} | "
            f"val_loss={val_metrics['val_loss']:.4f} | "
            f"ppl={val_metrics['perplexity']:.2f}\n"
        )

        last_path = checkpoint_dir / "cognitutor_s_last.pt"
        save_checkpoint(
            model=model,
            optimizer=optimizer,
            config=config,
            epoch=epoch,
            step=global_step,
            val_metrics=val_metrics,
            checkpoint_path=last_path,
        )

        if val_metrics["val_loss"] < best_val_loss:
            best_val_loss = val_metrics["val_loss"]

            best_path = checkpoint_dir / "cognitutor_s_best.pt"
            save_checkpoint(
                model=model,
                optimizer=optimizer,
                config=config,
                epoch=epoch,
                step=global_step,
                val_metrics=val_metrics,
                checkpoint_path=best_path,
            )

            print(f"Saved best checkpoint: {best_path}")

    print("\nTraining complete.")
    print(f"Best val loss: {best_val_loss:.4f}")
    print(f"Metrics: {metrics_path}")
    print(f"Last checkpoint: {checkpoint_dir / 'cognitutor_s_last.pt'}")
    print(f"Best checkpoint: {checkpoint_dir / 'cognitutor_s_best.pt'}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=str,
        default="configs/cognitutor_s.yaml",
        help="Path to config YAML file",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(ROOT_DIR / args.config)