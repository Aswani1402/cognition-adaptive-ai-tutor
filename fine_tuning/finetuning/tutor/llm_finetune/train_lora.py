from __future__ import annotations

import json
import os
from pathlib import Path

import torch

from datasets import Dataset

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)

from peft import (
    LoraConfig,
    get_peft_model,
    TaskType,
)


ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "training_data" / "llm_tutor"

MODEL_NAME = os.getenv(
    "TUTOR_BASE_MODEL",
    "HuggingFaceTB/SmolLM2-135M"
)

OUTPUT_DIR = Path(
    os.getenv(
        "TUTOR_OUTPUT_DIR",
        str(
            ROOT
            / "models"
            / "llm_finetuned"
            / "smollm2_135m_lora"
        )
    )
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

MAX_LENGTH = int(
    os.getenv("MAX_LENGTH", "256")
)

BATCH_SIZE = int(
    os.getenv("BATCH_SIZE", "2")
)

GRAD_ACCUM = int(
    os.getenv("GRAD_ACCUM", "4")
)

LEARNING_RATE = float(
    os.getenv("LEARNING_RATE", "2e-4")
)


def load_jsonl(path):

    rows = []

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            row = json.loads(line)

            # ======================================
            # FORCE OUTPUT TO STRING
            # ======================================

            if not isinstance(
                row["output"],
                str
            ):

                row["output"] = json.dumps(
                    row["output"],
                    ensure_ascii=False
                )

            rows.append(row)

    return rows


def format_data(example):

    input_data = example["input"]

    if not isinstance(input_data, str):

        input_data = json.dumps(
            input_data,
            ensure_ascii=False,
            indent=2
        )

    return {

        "text": f"""### Instruction
{example['instruction']}

### Input
{input_data}

### Response
{example['output']}"""
    }


def tokenize(example, tokenizer):

    return tokenizer(
        example["text"],
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length",
    )


def main():

    print("\nLoading dataset...\n")

    # ======================================
    # FAST TRAINING SUBSET
    # ======================================

    train_data = load_jsonl(
        DATA_DIR / "tutor_train.jsonl"
    )[:500]

    val_data = load_jsonl(
        DATA_DIR / "tutor_val.jsonl"
    )[:50]

    print(f"Train rows: {len(train_data)}")

    print(f"Validation rows: {len(val_data)}")

    dataset = {

        "train":
            Dataset.from_list(train_data),

        "validation":
            Dataset.from_list(val_data),
    }

    dataset["train"] = dataset[
        "train"
    ].map(format_data)

    dataset["validation"] = dataset[
        "validation"
    ].map(format_data)

    # ======================================
    # TOKENIZER
    # ======================================

    print("\nLoading tokenizer...\n")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME
    )

    if tokenizer.pad_token is None:

        tokenizer.pad_token = (
            tokenizer.eos_token
        )

    print("Tokenizer loaded.")

    # ======================================
    # MODEL
    # ======================================

    print("\nLoading base model...\n")

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME
    )

    print("Model loaded.")

    # ======================================
    # APPLY LORA
    # ======================================

    print("\nApplying LoRA...\n")

    lora_config = LoraConfig(

        task_type=TaskType.CAUSAL_LM,

        r=8,

        lora_alpha=16,

        lora_dropout=0.05,

        target_modules=[
            "q_proj",
            "v_proj",
        ],
    )

    model = get_peft_model(
        model,
        lora_config
    )

    model.print_trainable_parameters()

    # ======================================
    # TOKENIZE DATASET
    # ======================================

    print("\nTokenizing dataset...\n")

    tokenized = {

        "train":
            dataset["train"].map(
                lambda x: tokenize(
                    x,
                    tokenizer
                )
            ),

        "validation":
            dataset["validation"].map(
                lambda x: tokenize(
                    x,
                    tokenizer
                )
            ),
    }

    data_collator = (
        DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False
        )
    )

    # ======================================
    # TRAINING ARGS
    # ======================================

    training_args = TrainingArguments(

        output_dir=str(OUTPUT_DIR),

        per_device_train_batch_size=
            BATCH_SIZE,

        per_device_eval_batch_size=
            BATCH_SIZE,

        gradient_accumulation_steps=
            GRAD_ACCUM,

        max_steps=20,

        logging_steps=10,

        eval_strategy="steps",

        eval_steps=10,

        save_steps=20,

        save_total_limit=1,

        learning_rate=
            LEARNING_RATE,

        fp16=torch.cuda.is_available(),

        report_to="none",

        logging_dir=str(
            OUTPUT_DIR / "logs"
        ),
    )

    trainer = Trainer(

        model=model,

        args=training_args,

        train_dataset=
            tokenized["train"],

        eval_dataset=
            tokenized["validation"],

        data_collator=
            data_collator,
    )

    # ======================================
    # TRAIN
    # ======================================

    print("\nStarting training...\n")

    trainer.train()

    # ======================================
    # EVALUATE
    # ======================================

    print("\nRunning evaluation...\n")

    eval_results = trainer.evaluate()

    print(eval_results)

    # ======================================
    # SAVE
    # ======================================

    print("\nSaving model...\n")

    model.save_pretrained(
        OUTPUT_DIR
    )

    tokenizer.save_pretrained(
        OUTPUT_DIR
    )

    print("\nTraining complete!\n")


if __name__ == "__main__":

    main()