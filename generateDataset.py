import argparse
import os
import shlex
import shutil
import subprocess
from pathlib import Path

from tqdm import tqdm

from create_prompt_dataset import create_prompt_dataset


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = Path(BASE_DIR)

SUBSUMPTION_JAR = BASE_PATH / "lib" / "subsumption-analyzer-jar-with-dependencies.jar"
JUSTIFICATION_JAR = BASE_PATH / "lib" / "compute-justifications-with-dependencies.jar"


def run_command(command, cwd=BASE_PATH):
    print("+", " ".join(str(part) for part in command))
    subprocess.run([str(part) for part in command], cwd=cwd, check=True)


def parse_distances(raw_distances):
    distances = []
    for value in raw_distances.split(","):
        value = value.strip()
        if value:
            distances.append(int(value))
    if not distances:
        raise ValueError("At least one distance must be provided.")
    return distances


def java_command(java_opts, *args):
    return ["java", *shlex.split(java_opts), *args]


def get_java_major_version():
    completed = subprocess.run(
        ["java", "-version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    version_output = completed.stderr or completed.stdout
    first_line = version_output.splitlines()[0] if version_output.splitlines() else ""
    if '"' not in first_line:
        return None

    version = first_line.split('"')[1]
    if version.startswith("1."):
        return int(version.split(".")[1])
    return int(version.split(".")[0])


def initial_subsumptions(ont_file_path, subsumption_dir, java_opts):
    run_command(
        java_command(
            java_opts,
            "-jar",
            SUBSUMPTION_JAR,
            ont_file_path,
            subsumption_dir,
        )
    )


def validate_inputs(onto_file_path, run_retrieval):
    if not Path(onto_file_path).is_file():
        raise FileNotFoundError(f"Ontology file not found: {onto_file_path}")
    if not SUBSUMPTION_JAR.is_file():
        raise FileNotFoundError(f"Subsumption analyzer jar not found: {SUBSUMPTION_JAR}")
    if not JUSTIFICATION_JAR.is_file():
        raise FileNotFoundError(f"Justification jar not found: {JUSTIFICATION_JAR}")
    java_major = get_java_major_version()
    if java_major is None:
        raise RuntimeError("Unable to determine Java version from `java -version`.")
    if java_major < 22:
        raise RuntimeError(
            "Java 22 or newer is required by lib/compute-justifications-with-dependencies.jar "
            f"(detected Java {java_major})."
        )
    if run_retrieval and not (BASE_PATH / "BRIGHT").is_dir():
        raise FileNotFoundError(
            "BRIGHT is required for retrieval. Run scripts/setup_and_run.sh or "
            "clone https://github.com/xlang-ai/BRIGHT into ./BRIGHT."
        )


def main(
    onto_file_path,
    num_just,
    num_subsumptions,
    distance_list,
    skip_retrieval=False,
    retrieval_model="bge",
    subsumption_java_opts="-Xmx8g -Xms1g",
    justification_java_opts="-Xmx8g -Xms1g",
):
    validate_inputs(onto_file_path, run_retrieval=not skip_retrieval)
    ont_name = os.path.splitext(os.path.basename(onto_file_path))[0]
    subsumption_dir = f"subsumptions/{ont_name}/"

    # 1. Create the subsumption files for each distance.
    if not os.path.exists(subsumption_dir):
        print(f"Subsumption directory {subsumption_dir} does not exist. Creating it...")
        os.makedirs(subsumption_dir, exist_ok=True)
        initial_subsumptions(onto_file_path, subsumption_dir, subsumption_java_opts)
    else:
        print(f"Subsumption directory {subsumption_dir} already exists.")

    # 2. Compute justifications.
    print(f"Computing justifications for {ont_name}...")
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

        command = java_command(
            justification_java_opts,
            "--add-opens",
            "java.base/java.lang=ALL-UNNAMED",
            "--add-opens",
            "java.base/java.util=ALL-UNNAMED",
            "--add-opens",
            "java.base/java.lang.reflect=ALL-UNNAMED",
            "--add-opens",
            "java.base/java.text=ALL-UNNAMED",
            "--add-opens",
            "java.desktop/java.awt.font=ALL-UNNAMED",
            "-jar",
            JUSTIFICATION_JAR,
            onto_file_path,
            subsumption_file,
            output_dir,
            start_id,
            end_id,
            timeout,
            max_just,
        )
        run_command(command)

    # 3. Transfer the justifications to a RAG dataset.
    print(f"Transferring justifications to RAG dataset for {ont_name}...")
    from transfer_subsumption_justification import build_rag_dataset

    build_rag_dataset(distance_list, onto_file_path, subsumption_dir, justification_dir, "standard")

    if skip_retrieval:
        print("Skipping retrieval and prompt dataset creation because --skip_retrieval was set.")
        return

    # 4. Apply a retrieval model on the RAG dataset.
    print(f"Applying {retrieval_model} retrieval for {ont_name}...")
    for distance in tqdm(distance_list):
        run_command(
            [
                "python",
                "mimic_run.py",
                "--task",
                ont_name,
                "--model",
                retrieval_model,
                "--depth",
                distance,
            ]
        )

    # 5. Build the prompt dataset according to the RAG dataset.
    print(f"Building prompt dataset for {ont_name}...")
    create_prompt_dataset(ont_name, BASE_DIR, distance_list)

    # 6. Move the verbalization map into the final prompt dataset folder.
    source_map = BASE_PATH / "data" / f"{ont_name}_verbalization_map.json"
    target_map = BASE_PATH / "prompt_learning_dataset" / ont_name / "verbalization_map.json"
    if source_map.exists():
        target_map.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_map), str(target_map))
    else:
        print(f"Warning: verbalization map not found at {source_map}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the dataset")
    parser.add_argument("--ont", type=str, required=True, help="Path to the ontology file")
    parser.add_argument("--n_just", type=int, default=100, help="Number of justifications")
    parser.add_argument("--n_sub", type=int, default=50, help="Number of subsumptions")
    parser.add_argument(
        "--distances",
        type=str,
        default="4,6,8,10,12,14,16",
        help="Comma-separated atomic distances to process",
    )
    parser.add_argument(
        "--skip_retrieval",
        action="store_true",
        help="Stop after subsumptions, justifications, and RAG JSONL generation",
    )
    parser.add_argument(
        "--retrieval_model",
        type=str,
        default="bge",
        help="Retrieval model name passed to mimic_run.py",
    )
    parser.add_argument(
        "--subsumption_java_opts",
        type=str,
        default=os.environ.get("SUBSUMPTION_JAVA_OPTS", "-Xmx8g -Xms1g"),
        help="Java memory/options for the subsumption analyzer",
    )
    parser.add_argument(
        "--justification_java_opts",
        type=str,
        default=os.environ.get("JUSTIFICATION_JAVA_OPTS", "-Xmx8g -Xms1g"),
        help="Java memory/options for the justification computer",
    )

    args = parser.parse_args()

    main(
        args.ont,
        args.n_just,
        args.n_sub,
        parse_distances(args.distances),
        skip_retrieval=args.skip_retrieval,
        retrieval_model=args.retrieval_model,
        subsumption_java_opts=args.subsumption_java_opts,
        justification_java_opts=args.justification_java_opts,
    )
