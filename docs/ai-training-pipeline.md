# A.E.T.H.E.R Training & Fine-Tuning Pipeline (Starter)

This repo now includes starter code for custom model training/fine-tuning in `training_pipeline/`.

## Included components

- Dataset schema docs: `training_pipeline/data/schema.md`
- Dataset validator: `training_pipeline/scripts/validate_dataset.py`
- LoRA fine-tuning entrypoint: `training_pipeline/scripts/fine_tune_lora.py`
- Config template: `training_pipeline/config/train_config.example.yaml`
- Sample dataset: `training_pipeline/data/aether_train.sample.jsonl`

## Quick start

Validate dataset:

```bash
python training_pipeline/scripts/validate_dataset.py training_pipeline/data/aether_train.sample.jsonl
```

Run LoRA fine-tuning (requires `aether_sidecar[train]` dependencies):

```bash
python training_pipeline/scripts/fine_tune_lora.py --config training_pipeline/config/train_config.example.yaml
```
