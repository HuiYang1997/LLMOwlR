#!/usr/bin/env python3
import argparse
import os
from pathlib import Path

try:
    from huggingface_hub import HfApi
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: huggingface_hub. "
        "Install the project dependencies first with `python -m pip install -r requirements.txt`."
    ) from exc


def main():
    parser = argparse.ArgumentParser(description="Upload the prepared LLMOwlR dataset to Hugging Face.")
    parser.add_argument("--repo-id", default=os.environ.get("HF_REPO_ID"), help="Dataset repo id, e.g. HuiYang1997/LLMOwlR")
    parser.add_argument("--folder", default="huggingface", help="Folder to upload")
    parser.add_argument("--private", action="store_true", help="Create the dataset repo as private")
    parser.add_argument("--commit-message", default="Upload LLMOwlR prompt learning dataset")
    args = parser.parse_args()

    if not args.repo_id:
        raise SystemExit("Provide --repo-id or set HF_REPO_ID.")

    folder = Path(args.folder)
    data_dir = folder / "data"
    if not (folder / "README.md").is_file():
        raise FileNotFoundError(f"Dataset card not found: {folder / 'README.md'}")
    if not data_dir.is_dir() or not any(data_dir.glob("*.jsonl")):
        raise FileNotFoundError(
            f"Prepared JSONL files not found in {data_dir}. Run huggingface/prepare_dataset.py first."
        )

    api = HfApi()
    api.create_repo(repo_id=args.repo_id, repo_type="dataset", private=args.private, exist_ok=True)
    api.upload_folder(
        repo_id=args.repo_id,
        repo_type="dataset",
        folder_path=str(folder),
        commit_message=args.commit_message,
        ignore_patterns=["__pycache__/*", "*.pyc", ".DS_Store", "data/dataset_summary.json"],
        delete_patterns=["data/dataset_summary.json"],
    )

    print(f"Uploaded dataset to https://huggingface.co/datasets/{args.repo_id}")


if __name__ == "__main__":
    main()
