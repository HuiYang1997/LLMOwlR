#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple, Set, Any
from collections import defaultdict

def load_query_and_get_min_justification(query_file: str) -> Dict[str, Dict]:
    """
    Load queries from file and select the shortest justification for each query.
    
    Args:
        query_file: Path to query file
        
    Returns:
        Dictionary mapping query IDs to their minimal justifications
    """
    query_data = {}
    
    with open(query_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            query_id = data['id']
            justifications = data.get('justifications', [])
            
            # If no justifications, skip
            if not justifications or justifications == [["N/A"]]:
                continue
                
            # Find justification with minimal length
            min_justification = min(justifications, key=len) if justifications else []
            
            # Skip if justification length is less than 3
            if len(min_justification) < 3:
                continue
                
            query_data[query_id] = {
                'query': data['query'],
                'justification': min_justification,
                'golden_ids': data['golden_ids'],
                'conclusion': data['conclusion']
            }
    
    return query_data

def load_axiom_scores(score_file: str) -> Dict[str, Dict[str, float]]:
    """
    Load scores for each query from the score file.
    
    Args:
        score_file: Path to score file
        
    Returns:
        Dictionary mapping query IDs to dictionaries of axiom IDs and their scores
    """
    with open(score_file, 'r') as f:
        return json.load(f)

def get_noise_axioms(score_data: Dict[str, Dict[str, float]], 
                     justification_ids: List[str], 
                     k: int) -> List[str]:
    """
    Select top k axioms that aren't part of the justification.
    
    Args:
        score_data: Dictionary of axiom IDs and their scores
        justification_ids: List of axiom IDs that belong to the justification
        k: Maximum number of noise axioms to select
        
    Returns:
        List of selected noise axiom IDs
    """
    # Convert justification IDs to set for fast lookup
    justification_set = set(justification_ids)
    
    # Sort axioms by score, exclude justifications
    sorted_axioms = sorted(
        [(axiom_id, score) for axiom_id, score in score_data.items() 
         if axiom_id not in justification_set],
        key=lambda x: x[1],
        reverse=True
    )
    
    # Take top k axioms that aren't part of justifications
    return [axiom_id for axiom_id, _ in sorted_axioms[:k]]

def load_ontology_mapping(ontology_file: str) -> Dict[str, Dict[str, str]]:
    """
    Load ontology mapping from ID to content and axiom.
    
    Args:
        ontology_file: Path to ontology file
        
    Returns:
        Dictionary mapping IDs to content and axiom
    """
    ontology_map = {}
    
    with open(ontology_file, 'r') as f:
        for line in f:
            data = json.loads(line)
            ontology_map[data['id']] = {
                'content': data['content'],
                'axiom': data['axiom']
            }
    
    return ontology_map

def save_dataset(output_dir: str, data_dict: Dict[str, Tuple], query: Dict[str, str],
                 distance: int, mode: str) -> Tuple[Dict[str, List], Dict[int, Dict[str, List]]]:
    """
    Save the dataset and create index mapping.
    
    Args:
        output_dir: Directory to save the dataset
        data_dict: Dictionary mapping query IDs to tuples of (axiom_contents, justification_indices)
        query_data: Original query data
        distance: Distance value for filename
        random_names: Whether to use random names
        
    Returns:
        Tuple containing:
        - Dictionary mapping save paths to justification indices
        - Dictionary mapping justification lengths to paths and their justification IDs
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create mapping dictionaries
    path_to_justification_idx = {}
    length_to_paths = defaultdict(lambda: {"paths": [], "just_ids": []})
    
    for query_id, (axiom_ids, justification_idx) in data_dict.items():
        # Create filename based on query ID and parameters
        filename = f"query_{query_id}_d{distance}"
        if mode != 'true':
            filename += f"_{mode}"
        filename += ".json"
        
        save_path = os.path.join(output_dir, filename)
        
        # Save data
        with open(save_path, 'w') as f:
            json_obj = {
                "query": query[query_id],
                "axioms": axiom_ids
            }
            json.dump(json_obj, f, indent=2)
        
        # Add to mapping
        rel_path = os.path.relpath(save_path, os.path.dirname(output_dir))
        path_to_justification_idx[rel_path] = justification_idx
        
        # Add to length statistics
        just_length = len(justification_idx)
        length_to_paths[just_length]["paths"].append(rel_path)
        length_to_paths[just_length]["just_ids"].append(justification_idx)
    
    return path_to_justification_idx, length_to_paths

def create_prompt_dataset(ont_name, base_dir, distance_list):
    # Base directories
    prepare_data_dir = os.path.join(base_dir, "data")
    output_base_dir = os.path.join(base_dir, "outputs")
    
    # Directories for saving results
    result_dir = os.path.join(base_dir, "prompt_learning_dataset", ont_name)
    os.makedirs(result_dir, exist_ok=True)
    
    # Dictionary to store length statistics across all distances
    all_length_stats = {}
    
    # Process both true and random name datasets
    for mode in ['true', 'owl']:
        is_random = mode == 'random'
        random_suffix = f"_{mode}" if mode == 'random' else ""
        
        # Initialize length statistics for this mode
        length_stats = defaultdict(lambda: {"paths": [], "just_ids": []})
        
        # Determine directories based on mode
        example_dir = os.path.join(prepare_data_dir, 
                                  "example_random" if is_random else "example")
        ontology_file = os.path.join(prepare_data_dir, "documents", 
                                    f"{ont_name}{random_suffix}.jsonl")
        
        # Load ontology mapping
        print(f"Loading ontology from {ontology_file}")
        ontology_map = load_ontology_mapping(ontology_file)
        
        # Process each distance
        for distance in distance_list:  # Distances from 1 to 20
            # Set up paths
            query_file = os.path.join(example_dir, f"{ont_name}_d{distance}.jsonl")
            model_dir = os.path.join(output_base_dir, f"{ont_name}_d{distance}_bge_long_False")
            score_file = os.path.join(model_dir, "score.json")
            
            # Skip if necessary files don't exist
            if not os.path.exists(query_file) or not os.path.exists(score_file):
                print(f"Skipping distance {distance} - files not found")
                continue
                
            print(f"Processing distance {distance} {'(' + mode + ')' if mode != 'true' else ''}")
            
            # Load query data and select minimal justification
            print(query_file)
            query_data = load_query_and_get_min_justification(query_file)
            
            # Load scores
            score_data = load_axiom_scores(score_file)
            
            # Create output directory for this distance
            distance_dir = os.path.join(result_dir, f"d{distance}")
            os.makedirs(distance_dir, exist_ok=True)
            
            # Process each query
            data_with_justification_idx = {}
            query_with_id = {}
            
            for query_id, query_info in query_data.items():
                if query_id not in score_data:
                    continue
                    
                # Get justification IDs
                justification_ids = query_info['justification']
                if not justification_ids:
                    continue
                
                # Calculate how many noise axioms to get (min of 20 or justification length)
                k = len(justification_ids)
                justification_union = query_info['golden_ids']
                
                # Get noise axioms
                noise_axioms = get_noise_axioms(score_data[query_id], justification_union, k)
                assert len(noise_axioms) == k
                
                # Create combined list (justification + noise)
                all_axioms = justification_ids + noise_axioms
                
                # Convert IDs to axiom content
                axiom_contents = []
                justification_idx = []
                valid_axioms = True
                
                for i, axiom_id in enumerate(all_axioms):
                    if axiom_id in ontology_map:
                        # Skip if content and axiom are the same (non-EL axioms)
                        if ontology_map[axiom_id]['content'] == ontology_map[axiom_id]['axiom']:
                            valid_axioms = False
                            break
                            
                        if mode == 'owl':
                            axiom_contents.append(ontology_map[axiom_id]['axiom'])
                        else:
                            axiom_contents.append(ontology_map[axiom_id]['content'])
                        if i < len(justification_ids):  # If this is part of the justification
                            justification_idx.append(i)
                
                # Skip if any axiom had content identical to OWL axiom
                if not valid_axioms:
                    continue
                    
                # Skip if no axioms found
                if not axiom_contents:
                    continue
                    
                # Shuffle axioms
                combined = list(zip(axiom_contents, range(len(axiom_contents))))
                random.shuffle(combined)
                shuffled_axioms, original_indices = zip(*combined)
                
                # Update justification indices based on shuffle
                new_justification_idx = [original_indices.index(idx) for idx in justification_idx]
                
                data_with_justification_idx[query_id] = (shuffled_axioms, new_justification_idx)
            
                if mode == 'owl':
                    query = f"Extract the miminal support axioms for the conclusion: {query_data[query_id]['conclusion']}"
                else:
                    query = f"Extract the minimal support axioms for the conclusion: {query_data[query_id]['query']}"
                query_with_id[query_id] = query
            
            # Save dataset for this distance and get length statistics
            path_to_idx, dist_length_stats = save_dataset(
                distance_dir, 
                data_with_justification_idx, 
                query_with_id, 
                distance, 
                mode
            )
            
            # Save index mapping
            index_file = os.path.join(distance_dir, "justification_index.json")
            with open(index_file, 'w') as f:
                json.dump(path_to_idx, f, indent=2)
            
            # Merge length statistics from this distance
            for length, stats in dist_length_stats.items():
                length_stats[length]["paths"].extend(stats["paths"])
                length_stats[length]["just_ids"].extend(stats["just_ids"])
            
            print(f"Saved {len(path_to_idx)} items for distance {distance}")
        
        # Save length statistics for this mode
        # stats_filename = f"length_statistics{random_suffix}.json"
        # stats_path = os.path.join(result_dir, stats_filename)
        
        # # Convert defaultdict to true dict for JSON serialization
        serializable_stats = {str(k): v for k, v in length_stats.items()}
        
        # with open(stats_path, 'w') as f:
        #     json.dump(serializable_stats, f, indent=2)
        
        # print(f"Saved length statistics to {stats_path}")
        
        # Add to all stats
        all_length_stats[mode] = serializable_stats
    
    # Save combined statistics
    all_stats_path = os.path.join(result_dir, "all_length_statistics.json")
    with open(all_stats_path, 'w') as f:
        json.dump(all_length_stats, f, indent=2)
    
    print(f"Saved combined length statistics to {all_stats_path}")

if __name__ == "__main__":
    ont_name = "snomed-cleaned"
    main(ont_name)
