# Dataset Generation for Ontology Reasoning

This directory contains tools and scripts for generating datasets for ontology reasoning tasks.

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

### Main Dataset Generation Script

```bash
python generateDataset.py --ont <onto_file_path> --n_just <num_just> --n_sub <num_subsumptions>
```

Parameters:
- `onto_file_path`: Path to the ontology file (e.g., data/foodon.fss)
- `num_just`: Maximum number of justifications per subsumption (e.g., 100)
- `num_subsumptions`: Number of subsumptions to process (e.g., 50)


Example:
```bash
python generateDataset.py --ont data/foodon.fss --n_just 100 --n_sub 50
```


Note that the input ontology file should be in fss format. You could transfer any input ontology to the required form as follows:

```bash
java -jar lib/owl-to-fss-converter-1.0-SNAPSHOT.jar <input ont> <output_ont>
```

## Pipeline Steps

1. **Create subsumption files** for different distances
2. **Compute justifications** for subsumptions
3. **Transfer justifications to RAG dataset**
4. **Apply embedding models** (e.g., BGE) to compute distances for queries
5. **Build prompt datasets** based on the RAG datasets
6. **Move output files** to appropriate locations


## Directory Structure

- `BRIGHT/`: Contains the core retrieval functionality for embedding models
- `cache/`: Storage for computed embeddings and intermediate results
- `configs/`: Configuration files for RAG method
- `data/`: Input data files
- `justifications/`: Generated justifications for subsumption relationships
- `lib/`: Java libraries for ontology processing
- `outputs/`: Output files from mimic runs
- `subsumptions/`: Extracted subsumption relationships from ontologies
- `prompt_learning_dataset/`: (**FINAL DATASET**) Generated datasets for prompt learning
