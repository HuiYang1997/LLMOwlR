# LLMs for Ontology Proof (LLM4Proof)

↳ [Hugging Face Dataset](https://huggingface.co/datasets/Hui97/LLMOwlR)

Code for automatically generating and evaluating datasets for OWL ontology proof generation with large language models.

## Requirements

- Python 3.10+
- Java 22+ (the justification jar is compiled for Java class file version 66)
- Git (used by the one-click script to download BRIGHT)
- Python dependencies in `requirements.txt`

The core dependency stack includes DeepOnto, Hugging Face libraries, and PyTorch. The PyTorch/DeepOnto installation can be large, especially on GPU-enabled Linux systems. Java 21 can run the subsumption analyzer but fails at the justification stage; use Java 22 or newer for the full data-generation pipeline.

Retrieval dependencies are split out because some BRIGHT backends are heavy:

```bash
pip install -r requirements-retrieval.txt  # embedding/API retrieval backends
pip install -r requirements-bm25.txt       # optional BM25/pyserini backend
```

## One-Click Setup and Run

The script below installs the Python environment, downloads BRIGHT when it is missing, runs a small data-generation smoke test, and runs the analysis example:

```bash
./scripts/setup_and_run.sh
```

Useful options:

```bash
# Reuse packages already installed in the system Python environment.
USE_SYSTEM_SITE_PACKAGES=1 ./scripts/setup_and_run.sh

# Install retrieval dependencies as part of setup.
INSTALL_RETRIEVAL=1 ./scripts/setup_and_run.sh

# Install BM25/pyserini dependencies too.
INSTALL_RETRIEVAL=1 INSTALL_BM25=1 ./scripts/setup_and_run.sh

# Run generation on your own ontology instead of the small bundled example.
GENERATION_ARGS="--ont <your_ont_path!> --n_just 100 --n_sub 50" ./scripts/setup_and_run.sh

# Skip either part.
RUN_GENERATION=0 ./scripts/setup_and_run.sh
RUN_ANALYSIS=0 ./scripts/setup_and_run.sh

# Use an already prepared virtual environment without reinstalling packages.
SKIP_INSTALL=1 VENV_DIR=/path/to/venv ./scripts/setup_and_run.sh
```

The default generation command uses `data/example.fss`, `--n_just 1`, `--n_sub 1`, `--distances 4`, and `--skip_retrieval` so that the script can validate the Java/DeepOnto path without downloading embedding models. For the full pipeline, pass a real ontology and omit `--skip_retrieval`.

## Dataset

The dataset is available in two equivalent forms:

- [Hugging Face Dataset](https://huggingface.co/datasets/Hui97/LLMOwlR): recommended for browsing the data online or loading it with `datasets`.
- [prompt_learning_dataset.zip](prompt_learning_dataset.zip): the original zip archive used by this repository.

Load the Hugging Face version:

```python
from datasets import load_dataset

dataset = load_dataset("Hui97/LLMOwlR", split="test")
```

The Hugging Face version is organized for display and direct loading. The zip version preserves the original file layout, including `query_N_dX.json`, `query_N_dX_owl.json`, `justification_index.json`, `verbalization_map.json`, and `all_length_statistics.json`.

## Usage

### 1. Dataset Generation

Generate ontology reasoning datasets from OWL/FSS files:

```bash
python generateDataset.py --ont <ontology_file> --n_just <max_justifications> --n_sub <num_subsumptions>
```

Example:

```bash
python generateDataset.py --ont data/foodon.fss --n_just 100 --n_sub 50
```

Additional options:

- `--distances`: comma-separated atomic distances, default `4,6,8,10,12,14,16`
- `--skip_retrieval`: stop after subsumptions, justifications, and RAG JSONL generation
- `--retrieval_model`: retrieval model passed to `mimic_run.py`, default `bge`
- `--subsumption_java_opts` / `--justification_java_opts`: Java heap/options

### 2. Result Analysis

Analyze model outputs and compute performance metrics:

```bash
cd analyse_result
python analysis_script.py Qwen3-32B_output.json
```

The input JSON must contain `prompt`, `response`, and ground-truth IDs such as `correct_ids`.

## Directory Structure

- `BRIGHT/`: external retrieval dependency downloaded by `scripts/setup_and_run.sh`
- `cache/`: computed embeddings and intermediate retrieval cache
- `configs/`: retrieval model configuration files
- `data/`: input ontology files and generated RAG JSONL files
- `justifications/`: generated justifications for subsumption relationships
- `lib/`: Java libraries for ontology processing
- `outputs/`: retrieval output files
- `prompt_learning_dataset/`: generated prompt-learning dataset
- `subsumptions/`: extracted subsumption relationships from ontologies
- `analyse_result/`: model-output analysis scripts and examples
- `scripts/`: setup and run automation

## Citation

If you use this code or dataset, please cite:

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
