# LLMs for Ontology Proof （LLM4Proof）


The directory of codes for automatically generating and evaluating datasets for generating proofs with ontologies.


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

The data used in paper has been provided in `prompt_learning_dataset.zip`. The folder structure is of the form:

```
prompt_learning_dataset/
├── foodon/
│   ├── d4/
│   │   ├── justification_index.json
│   │   ├── query_0_d4.json
│   │   ├── query_0_d4_owl.json
│   │   └── ...
│   ├── d6/
│   ├── d8/
│   ├── d10/
│   ├── d12/
│   ├── d14/
│   ├── d16/
│   ├── verbalization_map.json
│   └── all_length_statistics.json
├── go-plus/
│   └── (same structure as foodon)
└── snomedCT/
    └── (same structure as foodon)
```

**Key Files:**

- **`dX/` directories** (e.g., `d4`, `d6`, `d10`): Atomic distance
  - **`query_N_dX.json`**: Natural language version of the reasoning task
  - **`query_N_dX_owl.json`**: OWL format version of the same reasoning task
  - **`justification_index.json`**: Maps each OWL query file to the indices of correct axioms (justifications)
- **`verbalization_map.json`**: Maps OWL URIs to human-readable labels for all entities in the ontology
- **`all_length_statistics.json`**: Statistics about query lengths and distributions across different depths



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



