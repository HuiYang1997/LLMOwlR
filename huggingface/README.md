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
---

# LLM4Proof Prompt Learning Dataset

This dataset contains prompt-learning samples for generating and evaluating OWL ontology proofs. It is derived from the `prompt_learning_dataset.zip` artifact in the LLMOwlR/LLM4Proof repository.

Each row contains a reasoning query, a shuffled list of candidate axioms, and the indices of the minimal support axioms in that shuffled list. Natural-language and OWL-formatted variants are represented as separate rows.

## Data Structure

The prepared Hugging Face layout is:

```text
huggingface/
├── README.md
├── data/
│   ├── foodon.jsonl
│   ├── go-plus.jsonl
│   ├── snomedCT.jsonl
│   └── dataset_summary.json
├── prepare_dataset.py
└── upload_dataset.py
```

JSONL columns:

- `ontology`: ontology subset name, such as `foodon`, `go-plus`, or `snomedCT`
- `distance`: atomic distance folder, such as `4`, `6`, or `10`
- `query_id`: source query id
- `format`: `natural_language` or `owl`
- `query`: prompt query
- `axioms`: shuffled candidate support axioms
- `correct_axiom_indices`: indices in `axioms` that form the gold support set
- `correct_axioms`: gold support axiom text resolved from `correct_axiom_indices`
- `source_path`: path inside the original zip archive

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
python huggingface/upload_dataset.py --repo-id HuiYang1997/LLMOwlR
```

The public dataset URL is expected to be:

```text
https://huggingface.co/datasets/HuiYang1997/LLMOwlR
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
