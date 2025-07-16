import os
import sys
import argparse
from tqdm import tqdm
from transfer_subsumption_justification import build_rag_dataset        
from create_prompt_dataset import create_prompt_dataset

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def initial_subsumptions(ont_file_path, subsumption_dir):
    command = f"java -Xmx64g -Xms12g -jar lib/subsumption-analyzer-jar-with-dependencies.jar {onto_file_path} {subsumption_dir}"
    os.system(command)

def main(onto_file_path, num_just, num_subsumptions, distance_list):
    ont_name = os.path.splitext(os.path.basename(onto_file_path))[0]
    output_dir_name = f"data/{ont_name}_result"
    subsumption_dir = f"subsumptions/{ont_name}/"

    # 1. create the subsumption files for different distance as in transfer_RAG.py
    if not os.path.exists(subsumption_dir):
        print(f"Subsumption directory {subsumption_dir} does not exist. Creating it...")
        initial_subsumptions(onto_file_path, subsumption_dir)
    else:
        print(f"Subsumption directory {subsumption_dir} already exists.")
    
    
    # 2. compute justifications
    print(f"Computing justifications for {ont_name}...")
    # mkdir -p justifications
    if not os.path.exists("justifications"):
        os.makedirs("justifications")
    
    start_id = 1
    end_id = num_subsumptions
    timeout = 30
    max_just = num_just
    
    justification_dir = "justifications"

    for distance in tqdm(distance_list):
        output_dir = f"{justification_dir}/{ont_name}_d{distance}"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        subsumption_file = f"{subsumption_dir}subsumptions_distance_d{distance}.txt"

        command = f"java -Xmx14g -Xms2g \
            --add-opens java.base/java.lang=ALL-UNNAMED \
            --add-opens java.base/java.util=ALL-UNNAMED \
            --add-opens java.base/java.lang.reflect=ALL-UNNAMED \
            --add-opens java.base/java.text=ALL-UNNAMED \
            --add-opens java.desktop/java.awt.font=ALL-UNNAMED \
            -jar lib/ComputeJustifications-with-dependencies.jar \
            {onto_file_path} \
            {subsumption_file} \
            {output_dir} \
            {start_id} \
            {end_id} \
            {timeout} \
            {max_just}"
        os.system(command)

    
    # 3. Transfer the justifications to RAG dataset
    print(f"Transferring justifications to RAG dataset for {ont_name}...")
    for distance in distance_list:
        build_rag_dataset(distance_list, onto_file_path, subsumption_dir, justification_dir, "standard")


    # 4. Apply BGE method on the RAG dataset compute distances of each query
    print(f"Applying BGE method for {ont_name}...")
    for distance in tqdm(distance_list):
        command = f"python mimic_run.py --task {ont_name} --model bge --depth {distance}"
        os.system(command)

    # 5. Build the prompt dataset according to the RAG dataset
    print(f"Building prompt dataset for {ont_name}...")
    create_prompt_dataset(ont_name, BASE_DIR, distance_list)

    # 6. move the file
    command = f"mv data/{ont_name}_verbalization_map.json prompt_learning_dataset/{ont_name}/verbalization_map.json"
    os.system(command)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the dataset")
    parser.add_argument("--ont", type=str, required=True,
                        help="Path to the ontology file")
    parser.add_argument("--n_just", type=int, default=100,
                        help="Number of justifications")
    parser.add_argument("--n_sub", type=int, default=50,
                        help="Number of subsumptions")
    
    args = parser.parse_args()
    
    onto_file_path = args.ont
    num_just = args.n_just
    num_sub = args.n_sub
    
    distance_list = list(range(4, 17, 2))
    
    main(onto_file_path, num_just, num_sub, distance_list)