---
pretty_name: LLM4Proof Prompt Learning Dataset
language:
- en
license: other
task_categories:
- text-generation
- question-answering
tags:
- ontology
- owl
- description-logic
- reasoning
- proof-generation
- llm4proof
configs:
- config_name: default
  data_files:
  - split: test
    path:
    - data/foodon.jsonl
    - data/go-plus.jsonl
    - data/snomedCT.jsonl
---

# LLM4Proof Prompt Learning Dataset

This dataset contains prompt-learning samples for generating and evaluating OWL ontology proofs. It is derived from the `prompt_learning_dataset.zip` artifact in the LLMOwlR/LLM4Proof repository.

Each row contains a reasoning query, a shuffled list of candidate axioms, and the indices of the minimal support axioms in that shuffled list. Natural-language and OWL-formatted variants are represented as separate rows.

## Atomic Distance

`atomic_distance` follows the metric used in the paper for selecting target conclusions. For an inferred atomic subsumption `A ⊑ B`, where `A` and `B` are atomic concepts, it is a heuristic estimate of reasoning length: roughly, the length of the shortest direct-subsumption chain connecting `A` to `B`, which also indicates about how many intermediate atomic concepts are needed between the two concepts. A direct subsumption has atomic distance `1`; larger values usually indicate longer or more complex reasoning.

## Dataset Viewer

The default configuration combines all three ontology subsets in one `test` split. Use the `ontology` column to filter for `foodon`, `go-plus`, or `snomedCT`.

| Configuration | Split | Rows | Source file |
| --- | --- | ---: | --- |
| `default` | `test` | 1,969 | `data/*.jsonl` |

```python
from datasets import load_dataset

dataset = load_dataset("Hui97/LLMOwlR", split="test")
foodon = dataset.filter(lambda row: row["ontology"] == "foodon")
```

## Data Structure

The prepared Hugging Face layout is:

```text
huggingface/
├── README.md
├── data/
│   ├── foodon.jsonl
│   ├── go-plus.jsonl
│   └── snomedCT.jsonl
├── metadata/
│   └── dataset_summary.json
├── prepare_dataset.py
└── upload_dataset.py
```

JSONL columns:

- `ontology`: ontology subset name, such as `foodon`, `go-plus`, or `snomedCT`
- `atomic_distance`: proof-distance bucket extracted from the original data; `foodon` and `go-plus` use `4, 6, 8, 10, 12, 14, 16`, while `snomedCT` uses `1` and `11`
- `query_id`: source query id
- `format`: `natural_language` or `owl`
- `query`: prompt query
- `axioms`: shuffled candidate support axioms
- `correct_axiom_indices`: indices in `axioms` that form the gold support set
- `correct_axioms`: gold support axiom text resolved from `correct_axiom_indices`
- `source_path`: path inside the original zip archive

Additional aggregate metadata is stored in `metadata/dataset_summary.json`. It is intentionally kept outside `data/` so that the Hugging Face dataset viewer only parses the JSONL data files.

## Preparation

From the repository root:

```bash
python huggingface/prepare_dataset.py \
  --input prompt_learning_dataset.zip \
  --output huggingface/data
```

## Upload

Authenticate first:

```bash
export HF_TOKEN=<your_hugging_face_token>
```

Then upload:

```bash
python huggingface/upload_dataset.py --repo-id Hui97/LLMOwlR
```

The public dataset URL is:

```text
https://huggingface.co/datasets/Hui97/LLMOwlR
```

Override the target with `--repo-id` or `HF_REPO_ID` if the dataset should live under a different Hugging Face namespace.

## Citation

```bibtex
@inproceedings{yang2026large,
  title = {Large Language Model for OWL Proofs},
  author = {Yang, Hui and Chen, Jiaoyan and Sattler, Uli},
  booktitle = {Proceedings of the ACM Web Conference 2026},
  pages = {3952--3963},
  year = {2026},
  publisher = {ACM},
  doi = {10.1145/3774904.3792395},
  url = {https://doi.org/10.1145/3774904.3792395}
}
```
