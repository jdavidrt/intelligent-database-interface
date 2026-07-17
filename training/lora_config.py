"""Shared LoRA training configuration — hyperparameters per MASTERPLAN.md §8.

Imported by training/colab_train_adapter.ipynb (and any future local trainer) so
the recipe lives in exactly one place. QLoRA 4-bit on Qwen2.5-Coder-3B-Instruct,
targeting attention + MLP projections; exported to GGUF and served by llama.cpp
alongside the Q4_K_M base (VRAM budget < 3.5 GB with an active adapter).
"""

from __future__ import annotations

BASE_MODEL = "unsloth/Qwen2.5-Coder-3B-Instruct-bnb-4bit"
# HF repo used by llama.cpp's convert_lora_to_gguf.py as the --base reference.
BASE_MODEL_FOR_GGUF = "Qwen/Qwen2.5-Coder-3B-Instruct"

MAX_SEQ_LENGTH = 4096  # runtime prompts carry the full 19-table schema summary

LORA = {
    "r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "target_modules": [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",  # attention
        "gate_proj",
        "up_proj",
        "down_proj",  # MLP
    ],
    "bias": "none",
    "use_gradient_checkpointing": "unsloth",
}

TRAINING = {
    "num_train_epochs": 3,
    "learning_rate": 2e-4,
    "per_device_train_batch_size": 2,
    "gradient_accumulation_steps": 4,  # effective batch 8
    "warmup_ratio": 0.05,
    "lr_scheduler_type": "cosine",
    "optim": "adamw_8bit",
    "weight_decay": 0.01,
    "logging_steps": 10,
    "seed": 42,
}

# Qwen2.5 chat-template markers for Unsloth's train_on_responses_only(): the loss
# is computed ONLY on the assistant completion, never on the schema-heavy prompt.
INSTRUCTION_PART = "<|im_start|>user\n"
RESPONSE_PART = "<|im_start|>assistant\n"

# Agent -> dataset file stems under data/synthetic/ (built by build_dataset.py).
ADAPTERS = {
    "sql_generator": {
        "train_file": "sql_generator_train.jsonl",
        "eval_file": "sql_generator_eval.jsonl",
        # External mix: gretelai/synthetic_text_to_sql rows formatted by
        # build_dataset.format_gretel_example(); soundwave stays the majority.
        "gretel_mix_examples": 350,
    },
    "query_understanding": {
        "train_file": "query_understanding_train.jsonl",
        "eval_file": "query_understanding_eval.jsonl",
        "gretel_mix_examples": 0,  # intent JSON has no external equivalent
    },
}
