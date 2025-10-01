# Dataset Generation for Ontology Reasoning

This directory contains tools and scripts for generating datasets for ontology reasoning tasks.

## Overview

The dataset generation pipeline processes ontology files (in OWL/FSS format) and produces various datasets for ontology reasoning tasks:
1. Extracts subsumption relationships from ontologies
2. Computes justifications for these subsumptions
3. Transforms justifications into RAG datasets
4. Creates prompt datasets for language models

## Requirements

- Download BRIGHT from https://github.com/xlang-ai/BRIGHT
- Python libraries:
  - Requirment of BRIGHT (https://github.com/xlang-ai/BRIGHT)
  - deeponto
  - pandas
  - tqdm
  - numpy
  - transformers
  - datasets


## Directory Structure

- `BRIGHT/`: Contains the core retrieval functionality for embedding models
- `cache/`: Storage for computed embeddings and intermediate results
- `configs/`: Configuration files for different models
- `data/`: Input and output data files
- `justifications/`: Generated justifications for subsumption relationships
- `lib/`: Java libraries for ontology processing
- `outputs/`: Output files from mimic runs
- `prompt_learning_dataset/`: (**FINAL DATASET**) Generated datasets for prompt learning
- `subsumptions/`: Extracted subsumption relationships from ontologies
- `analyse_result/`: Analyse the output result



## Usage

### 1. Dataset Generation

Generate ontology reasoning datasets from OWL/FSS files:

```bash
python generateDataset.py --ont <ontology_file> --n_just <max_justifications> --n_sub <num_subsumptions>
```

**Parameters:**
- `--ont`: Path to the ontology file (OWL/FSS format)
- `--n_just`: Maximum number of justifications to compute per subsumption
- `--n_sub`: Number of subsumption relationships to process

**Example:**
```bash
python generateDataset.py --ont data/foodon.fss --n_just 100 --n_sub 50
```

This command processes the FoodOn ontology, extracting 50 subsumption relationships and computing up to 100 justifications for each.

### 2. Result Analysis

Analyze model outputs and compute performance metrics:

```bash
cd analyse_result
python analysis_script.py <output_file>
```

**Parameters:**
- `<output_file>`: Path to the model output JSON file (must contain input, responce, and ground truth IDs)

**Example:**
```bash
cd analyse_result
python analysis_script.py Qwen3-32B_output.json
```

This script evaluates the model's reasoning performance by comparing predicted justifications against ground truth annotations.





