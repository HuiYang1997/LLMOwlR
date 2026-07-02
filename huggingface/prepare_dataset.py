#!/usr/bin/env python3
import argparse
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path


QUERY_RE = re.compile(r"^prompt_learning_dataset/([^/]+)/(d(\d+))/(query_(.+)_d\d+(?:_owl)?\.json)$")


def load_json_from_zip(zip_file, member):
    with zip_file.open(member) as handle:
        return json.loads(handle.read().decode("utf-8"))


def build_index_lookup(zip_file, ontology):
    lookup = {}
    prefix = f"prompt_learning_dataset/{ontology}/"

    for member in zip_file.namelist():
        if not member.startswith(prefix) or not member.endswith("justification_index.json"):
            continue
        index_data = load_json_from_zip(zip_file, member)
        for rel_path, indices in index_data.items():
            lookup[rel_path] = indices

    stats_member = f"{prefix}all_length_statistics.json"
    if stats_member in zip_file.namelist():
        stats = load_json_from_zip(zip_file, stats_member)
        for mode_data in stats.values():
            for length_data in mode_data.values():
                paths = length_data.get("paths", [])
                just_ids = length_data.get("just_ids", [])
                for rel_path, indices in zip(paths, just_ids):
                    lookup.setdefault(rel_path, indices)

    return lookup


def iter_rows(zip_path):
    with zipfile.ZipFile(zip_path) as zip_file:
        members = [
            member
            for member in zip_file.namelist()
            if member.startswith("prompt_learning_dataset/")
            and "__MACOSX" not in member
            and member.endswith(".json")
        ]
        ontologies = sorted({member.split("/")[1] for member in members if len(member.split("/")) > 2})
        index_by_ontology = {
            ontology: build_index_lookup(zip_file, ontology)
            for ontology in ontologies
        }

        for member in sorted(members):
            match = QUERY_RE.match(member)
            if not match:
                continue

            ontology, distance_dir, distance, filename = match.group(1), match.group(2), int(match.group(3)), match.group(4)
            rel_path = f"{distance_dir}/{filename}"
            sample = load_json_from_zip(zip_file, member)
            indices = index_by_ontology.get(ontology, {}).get(rel_path)
            axioms = sample.get("axioms", [])
            correct_axioms = []
            if isinstance(indices, list):
                correct_axioms = [
                    axioms[index]
                    for index in indices
                    if isinstance(index, int) and 0 <= index < len(axioms)
                ]

            yield {
                "ontology": ontology,
                "distance": distance,
                "query_id": filename.split("_d")[0].replace("query_", ""),
                "format": "owl" if filename.endswith("_owl.json") else "natural_language",
                "query": sample.get("query", ""),
                "axioms": axioms,
                "correct_axiom_indices": indices,
                "correct_axioms": correct_axioms,
                "source_path": member,
            }


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Prepare LLMOwlR data for Hugging Face Datasets.")
    parser.add_argument("--input", default="prompt_learning_dataset.zip", help="Source prompt dataset zip")
    parser.add_argument("--output", default="huggingface/data", help="Output folder for JSONL files")
    args = parser.parse_args()

    zip_path = Path(args.input)
    output_dir = Path(args.output)
    if not zip_path.is_file():
        raise FileNotFoundError(f"Input zip not found: {zip_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    rows_by_ontology = defaultdict(list)
    for row in iter_rows(zip_path):
        rows_by_ontology[row["ontology"]].append(row)

    summary = {
        "source": str(zip_path),
        "ontologies": {},
        "total_rows": 0,
    }

    for ontology, rows in sorted(rows_by_ontology.items()):
        rows.sort(key=lambda row: (row["distance"], row["format"], row["query_id"]))
        output_path = output_dir / f"{ontology}.jsonl"
        write_jsonl(output_path, rows)
        summary["ontologies"][ontology] = {
            "rows": len(rows),
            "file": output_path.name,
            "distances": sorted({row["distance"] for row in rows}),
            "formats": sorted({row["format"] for row in rows}),
        }
        summary["total_rows"] += len(rows)

    with (output_dir / "dataset_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    print(f"Wrote {summary['total_rows']} rows to {output_dir}")


if __name__ == "__main__":
    main()
