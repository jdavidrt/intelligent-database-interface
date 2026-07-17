# Synthetic training datasets (LoRA fine-tuning)

Built by `python training/build_dataset.py` from the 30 hand-verified gold pairs in
`databases/soundwave/03_soundwave_edge_cases.md` plus the authored augmentation in
`training/soundwave_augmentation.py` (paraphrases, value substitutions, EC-02/EC-04
targeted oversampling). Consumed by `training/colab_train_adapter.ipynb`.

| File | Contents |
|---|---|
| `sql_generator_train.jsonl` | NL → `### Rationale / ### SQL` pairs, runtime prompt format |
| `sql_generator_eval.jsonl` | Held-out: gold originals + gate_d1 probe wordings — never trained on |
| `query_understanding_train.jsonl` | NL → Intent-JSON pairs (entities/metrics/filters/ambiguity) |
| `query_understanding_eval.jsonl` | Held-out intent split |
| `dataset_stats.json` | Per-file example counts + execution-validation tallies |

Every SQL target was execution-validated against the FileConnector's in-memory SQLite.
Each record: `{"messages": [system, user, assistant], "meta": {id, ec, split, validated,
result_rows, nl, gold_sql}}` — `messages` is what the trainer consumes.

Regenerate after changing the gold catalog, the survey, or the agents' prompt formats
(the datasets must always mirror the exact runtime prompts).
