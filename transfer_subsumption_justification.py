#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Subsumption and Justification Transfer Algorithm

This script processes ontology files together with subsumption and justification data
to create RAG datasets. It requires the deeponto library for ontology processing.

Usage:
    python transfer_subsumption_justification.py --owl <path_to_owl_file> \
        --subsumptions <path_to_subsumptions_dir> \
        --justifications <path_to_justifications_dir> \
        [--verbalization_mode standard|random]

Dependencies:
    - deeponto
    - pandas
    - tqdm
"""

import os
import json
import re
import gc
import time
import sys
import itertools
from pathlib import Path
import shutil
import random
import string
import uuid
import hashlib
import argparse
import pandas as pd
from tqdm import tqdm
from typing import Dict, List, Tuple, Set, Optional

# 设置环境变量以避免交互式提示JVM内存大小和增加JVM内存
os.environ['JAVA_TOOL_OPTIONS'] = '-Xmx12g'

from deeponto.onto.ontology import Ontology
from deeponto.onto.verbalisation import OntologyVerbaliser

def verbalize_axioms(ontology: Ontology, verbaliser: OntologyVerbaliser, save_vocab_map: bool = True, vocab_map_path: str = None) -> Dict[str, Dict]:
    """
    Extract and verbalize logical axioms from the ontology.
    
    Args:
        ontology: The loaded ontology
        verbaliser: The ontology verbaliser
        save_vocab_map: Whether to save the verbalization mapping to a file
        vocab_map_path: Path to save the verbalization mapping (if None, will use default path)
        
    Returns:
        Dictionary mapping axiom IDs to their details (original axiom and verbalization)
    """
    print("Verbalizing logical axioms...")
    axioms_dict = {}
    axiom_id = 0
    
    # 记录不同类型公理的数量
    axiom_types_count = {}
    successful_verbalization_count = 0
    failed_verbalization_count = 0
    
    # 记录示例公理和其自然语言表示（用于调试）
    example_verbalizations = {}
    
    # Process all logical axioms in the ontology
    all_axioms = list(ontology.get_all_axioms())
    print(f"总共找到 {len(all_axioms)} 个公理")
    
    for axiom in tqdm(all_axioms):
        axiom_str = str(axiom)
        axiom_type = "Unknown"
        
        # 确定公理类型
        if axiom_str.startswith("SubClassOf("):
            axiom_type = "SubClassOf"
        elif axiom_str.startswith("EquivalentClasses("):
            axiom_type = "EquivalentClasses"
        elif axiom_str.startswith("ObjectPropertyDomain("):
            axiom_type = "ObjectPropertyDomain"
        elif axiom_str.startswith("ObjectPropertyRange("):
            axiom_type = "ObjectPropertyRange"
        elif axiom_str.startswith("SubObjectPropertyOf("):
            axiom_type = "SubObjectPropertyOf"
        # elif axiom_str.startswith("DisjointClasses("):
        #     axiom_type = "DisjointClasses"
        # elif axiom_str.startswith("InverseObjectProperties("):
        #     axiom_type = "InverseObjectProperties"
        # elif axiom_str.startswith("InverseFunctionalObjectProperty("):
        #     axiom_type = "InverseFunctionalObjectProperty"
        # elif axiom_str.startswith("FunctionalObjectProperty("):
        #     axiom_type = "FunctionalObjectProperty"
        # elif axiom_str.startswith("InverseTransitiveObjectProperty("):
        #     axiom_type = "InverseTransitiveObjectProperty"
        elif axiom_str.startswith("TransitiveObjectProperty("):
            axiom_type = "TransitiveObjectProperty"
        else:
            failed_verbalization_count += 1
            continue
        
        # 更新公理类型计数
        if axiom_type in axiom_types_count:
            axiom_types_count[axiom_type] += 1
        else:
            axiom_types_count[axiom_type] = 1
        
        # Verbalize the axiom based on its type
        verbalization_str = ""
        
        try:
            # Check axiom type and call appropriate verbalisation method
            if axiom_type == "SubClassOf":
                verbalization = verbaliser.verbalise_class_subsumption_axiom(axiom)
                verbalization_str = f"{verbalization[0]['verbal']} is a subclass of {verbalization[1]['verbal']}"
            elif axiom_type == "EquivalentClasses":
                verbalization = verbaliser.verbalise_class_equivalence_axiom(axiom)
                verbalization_str = f"{verbalization[0]['verbal']} is equivalent to {verbalization[1]['verbal']}"
            elif axiom_type == "ObjectPropertyDomain":
                verbalization = verbaliser.verbalise_object_property_domain_axiom(axiom)
                verbalization_str = f"the property {verbalization[0]['verbal']} has domain {verbalization[1]['verbal']}"
            elif axiom_type == "ObjectPropertyRange":
                verbalization = verbaliser.verbalise_object_property_range_axiom(axiom)
                verbalization_str = f"the property {verbalization[0]['verbal']} has range {verbalization[1]['verbal']}"
            elif axiom_type == "SubObjectPropertyOf":
                verbalization = verbaliser.verbalise_object_property_subsumption_axiom(axiom)
                verbalization_str = f"{verbalization[0]['verbal']} is a sub-property of {verbalization[1]['verbal']}"
            elif axiom_type == "InverseObjectProperties":
                # get the IRIs of properties in axiom
                property_iris = axiom_str.split("InverseObjectProperties")[1][1:-1].split(" ")
                property_names = [verbaliser.vocab[property_iri[1:-1]] for property_iri in property_iris]
                verbalization_str = f"{property_names[0]} is the inverse of {property_names[1]}"
            elif axiom_type == "InverseFunctionalObjectProperty":
                # get the IRI of property in axiom
                property_iri = axiom_str.split("InverseFunctionalObjectProperty")[1][1:-1]
                property_name = verbaliser.vocab[property_iri[1:-1]]
                verbalization_str = f"the inverse of {property_name} is functional"
            elif axiom_type == "FunctionalObjectProperty":
                # get the IRI of property in axiom
                property_iri = axiom_str.split("FunctionalObjectProperty")[1][1:-1]
                property_name = verbaliser.vocab[property_iri[1:-1]]
                verbalization_str = f"{property_name} is a functional property"
            elif axiom_type == "InverseTransitiveObjectProperty":
                # get the IRI of property in axiom
                property_iri = axiom_str.split("InverseTransitiveObjectProperty")[1][1:-1]
                property_name = verbaliser.vocab[property_iri[1:-1]]
                verbalization_str = f"the inverse of {property_name} is transitive"
            elif axiom_type == "TransitiveObjectProperty":
                # get the IRI of property in axiom
                property_iri = axiom_str.split("TransitiveObjectProperty")[1][1:-1]
                property_name = verbaliser.vocab[property_iri[1:-1]]
                verbalization_str = f"{property_name} is a transitive property"
        except Exception as e:
            verbalization_str = axiom_str
            print(f"Error verbalizing axiom {axiom_str}: {str(e)}")

       
        # 保存示例（用于调试）
        if axiom_type not in example_verbalizations and verbalization_str:
            example_verbalizations[axiom_type] = (axiom_str, verbalization_str)
        successful_verbalization_count += 1

        
        # Store the axiom with a unique ID
        axiom_id_str = f"axiom_{axiom_id}"
        axioms_dict[axiom_id_str] = {
            "id": axiom_id_str,
            "axiom": axiom_str,
            "verbalization": verbalization_str,
            "axiom_type": axiom_type
        }
        axiom_id += 1
    
    # 打印公理类型统计信息
    print(f"\n公理类型统计:")
    for axiom_type, count in sorted(axiom_types_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {axiom_type}: {count}")
    
    print(f"\n自然语言转换结果:")
    print(f"  - 成功: {successful_verbalization_count}")
    print(f"  - 失败: {failed_verbalization_count}")
    print(f"  - 总共: {successful_verbalization_count + failed_verbalization_count}")
    
    # 打印示例（用于调试）
    print("\n示例公理自然语言表示:")
    for axiom_type, (axiom_str, verbalization) in example_verbalizations.items():
        print(f"\n类型: {axiom_type}")
        print(f"公理: {axiom_str}")
        print(f"自然语言: {verbalization}")
    
    print(f"\n总共保存了 {len(axioms_dict)} 个已转换公理")
    return axioms_dict


def load_subsumptions(subsumption_dir: str, k: int = 300) -> Dict[int, List[Tuple[str, str]]]:
    """
    Load subsumptions from a directory containing subsumption files.
    
    Args:
        subsumption_dir: Path to the directory containing subsumption files
        
    Returns:
        DataFrame containing subsumption information
    """
    print(f"Loading subsumptions from {subsumption_dir}...")
    
    # Check if directory exists
    if not os.path.exists(subsumption_dir):
        print(f"Error: Subsumption directory {subsumption_dir} does not exist")
        return pd.DataFrame()
    
    # Find all TSV or TXT files in the directory
    subsumption_files = []
    for root, dirs, files in os.walk(subsumption_dir):
        for file in files:
            if file.endswith('.tsv') or file.endswith('.txt'):
                subsumption_files.append(os.path.join(root, file))
    
    if not subsumption_files:
        print(f"No subsumption files found in {subsumption_dir}")
        return pd.DataFrame()
    
    print(f"Found {len(subsumption_files)} subsumption files")
    
    # Load and concatenate all subsumption files
    all_subsumptions = {}
    for file_path in tqdm(subsumption_files):
        dist_subsumption = int(file_path.split('_d')[-1].split('.')[0])

        subsumptions_list = []
        with open(file_path, 'r') as f:
            for line in f.readlines()[:k]:
                subsumer, subsumee = line.strip().split(' ')
                subsumptions_list.append((subsumer, subsumee))
        
        all_subsumptions[dist_subsumption] = subsumptions_list
    
    return all_subsumptions


def rearrange_owl(axiom: str) -> str:
    # 创建一个临时owl字符串，包含公理
    temp_owl = f'''Prefix(:=<http://example.org/>)\nPrefix(owl:=<http://www.w3.org/2002/07/owl#>)\nPrefix(rdf:=<http://www.w3.org/1999/02/22-rdf-syntax-ns#>)\nPrefix(xml:=<http://www.w3.org/XML/1998/namespace>)\nPrefix(xsd:=<http://www.w3.org/2001/XMLSchema#>)\nPrefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>)\n\nOntology(<http://example.org/temp>\n{axiom}\n)\n'''
                
    # 将临时OWL字符串写入临时文件
    temp_file = f"temp_axiom_{random.randint(1000, 9999)}.owl"
    with open(temp_file, 'w') as f:
        f.write(temp_owl)
                
    temp_onto = Ontology(temp_file)
    # 提取标准化的公理字符串
    axioms = [str(ax) for ax in temp_onto.get_all_axioms()]
    assert len(axioms) == 1
                
    # 删除临时文件
    os.remove(temp_file)
                
    rearranged_axiom = axioms[0]
    # print("rearrange to:", rearranged_axiom)
    return rearranged_axiom
    

def process_justification_file(file_path: str, axioms_dict: Dict[str, Dict], force_find: bool = False) -> List[str]:
    """
    Process a justification file and extract axiom IDs.
    
    Args:
        file_path: Path to the justification file
        axioms_dict: Dictionary mapping axiom strings to their IDs
        force_find: If True, raise an exception if an axiom is not found in the dictionary
        
    Returns:
        List of axiom IDs in the justification
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Create a reverse mapping from axiom string to ID for lookup
    axiom_to_id = {}
    for axiom_id, data in axioms_dict.items():
        axiom_str = data['axiom']
        axiom_to_id[axiom_str] = axiom_id
    
    # Extract axioms from the file
    # First, split content into lines and filter out unwanted lines
    axioms_in_file = content[:-1].split('\n')
    
    # Map axioms to their IDs
    axiom_ids = []
    found_count = 0
    missing_count = 0
    
    for axiom in axioms_in_file:
        if axiom in axiom_to_id:
            axiom_ids.append(axiom_to_id[axiom])
            found_count += 1
        else:
            # print("未找到公理: ", axiom, "Try to rearrange it.")
            # 尝试重新排列InverseObjectProperties或ObjectIntersectionOf中的项目
            rearranged_axiom = None

            filter_keywords = ["FunctionalObjectProperty(", "InverseObjectProperties(", "DisjointClasses(", "HasValue("]
            assert not any(keyword in axiom for keyword in filter_keywords)
            # if not force_find and any(keyword in axiom for keyword in filter_keywords):
            #     continue

            # print("rearranging....")
            rearranged_axiom = rearrange_owl(axiom)
            
            # 如果找到了标准化的公理并且它在字典中
            if rearranged_axiom and rearranged_axiom in axiom_to_id:
                axiom_ids.append(axiom_to_id[rearranged_axiom])
                found_count += 1
            else:
                if force_find:
                    print(f"严重错误: 公理 {axiom} 在 {file_path} 中未在公理字典中找到")
                    assert False
                
                missing_count += 1
                print(f"警告: 公理 {axiom} 在 {file_path} 中未在公理字典中找到")
    
    return axiom_ids


def load_ontology(owl_file_path: str, verbalization_mode: str = "standard") -> Tuple[Ontology, OntologyVerbaliser]:
    """
    Load an ontology from an OWL file and create a verbaliser for it.
    
    Args:
        owl_file_path: Path to the OWL file
        verbalization_mode: Mode for verbalization. Options:
            - "standard": Use standard vocab from labels as deeponto does (default)
            - "iri": Use IRI names when there are no labels
            - "random": Use randomly generated fake names as vocab
        
    Returns:
        Tuple of (ontology, verbaliser)
    """
    print(f"Loading ontology from {owl_file_path}...")
    print(f"Using verbalization mode: {verbalization_mode}")
    
    ontology = Ontology(owl_file_path)
    verbaliser = OntologyVerbaliser(ontology)
    
    entity_iris = list(ontology.owl_classes.keys()) + list(ontology.owl_object_properties.keys())
    
    # 额外处理：提取 IRI 的最后部分作为名称
    for entity_iri in entity_iris:
        # 检查是否有标签
        if entity_iri not in verbaliser.vocab or verbaliser.vocab[entity_iri] == entity_iri:  # 如果没有标签或使用了完整IRI
            if '#' in entity_iri:
                name = entity_iri.split('#')[-1]
                verbaliser.update_entity_name(entity_iri, name)
            elif '/' in entity_iri:
                name = entity_iri.split('/')[-1]
                verbaliser.update_entity_name(entity_iri, name)
    
    #save verbalization mapping to JSON file
    vocab_map_path = os.path.join(os.path.dirname(owl_file_path), f"{os.path.splitext(os.path.basename(owl_file_path))[0]}_verbalization_map.json")
    print(f"save {len(verbaliser.vocab)} items to {vocab_map_path}")
    with open(vocab_map_path, 'w', encoding='utf-8') as f:
        json.dump(verbaliser.vocab, f, ensure_ascii=False)

    if verbalization_mode == "random":
        concept_iris = list(ontology.owl_classes.keys())
        
        # 使用UUID或哈希方式替换概念名称
        used_names = set()  # 用于跟踪已使用的名称，虽然使用UUID几乎不可能重复
        
        for i, entity_iri in enumerate(concept_iris):
            # 方法1：使用UUID生成唯一名称（去掉连字符，取前16个字符）
            random_name = str(uuid.uuid4()).replace('-', '')[:10]
            
            # 方法2：使用哈希方式，基于实体IRI和索引生成唯一名称
            # hash_input = f"{entity_iri}_{i}"
            # hash_hex = hashlib.md5(hash_input.encode()).hexdigest()[:10]
            # random_name = hash_hex
            
            # 添加到已使用名称集合（UUID/哈希基本不会重复，但以防万一）
            if random_name in used_names:
                # 在极少数情况下发生冲突，添加索引后重新哈希
                random_name = hashlib.md5(f"{random_name}_{len(used_names)}".encode()).hexdigest()[:10]
            
            used_names.add(random_name)
            verbaliser.update_entity_name(entity_iri, random_name)

    return ontology, verbaliser


def save_axioms_as_text_files(axioms_dict: Dict, output_dir: str, ontology_name: str):
    """
    将所有公理的自然语言描述保存为单个JSONL文件
    
    Args:
        axioms_dict: 包含公理及其自然语言描述的字典
        output_dir: 输出目录的路径
        ontology_name: 本体名称
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建JSONL文件路径
    jsonl_file_path = os.path.join(output_dir, f"{ontology_name}.jsonl")
    
    print(f"保存公理自然语言描述到 {jsonl_file_path}...")
    
    # 保存所有公理的自然语言描述为一个JSONL文件
    count = 0
    with open(jsonl_file_path, "w") as f:
        for axiom_id, axiom_info in axioms_dict.items():
            # 仅处理有自然语言描述的公理
            if axiom_info.get("verbalization"):
                # 创建包含id和content的记录
                record = {
                    "id": axiom_id.split('_')[1],
                    "content": axiom_info['verbalization'],
                    "axiom": axiom_info['axiom'],
                }
                
                # 写入一行JSON
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
    
    print(f"总共保存了 {count} 条公理自然语言描述记录")
    print(f"文件保存在：{jsonl_file_path}")
    print(f"JSONL文件格式：每行一个JSON对象，包含'id'和'content'两个字段")
    
    # 返回JSONL文件路径，以便后续处理
    return jsonl_file_path


def create_hf_dataset(subsumption_list, axioms_dir: str, ontology_name: str, output_dir: str, distance: int) -> str:
    """
    从子集关系映射创建HuggingFace格式的数据集
    
    Args:
        subsumption_list: 子集关系到证明的映射
        axioms_dir: 公理自然语言描述文本文件所在目录
        ontology_name: 本体名称
        output_dir: 输出目录
        distance: 子集关系的距离
        
    Returns:
        数据集目录路径
    """
    
    print(f"开始创建HuggingFace数据集...")
    
    # 准备数据集记录
    dataset_records = []
    
    # 确保公理目录存在
    axioms_doc_dir = os.path.join(axioms_dir, f"{ontology_name}.jsonl")
    if not os.path.exists(axioms_doc_dir):
        print(f"Error: 公理自然语言描述目录 {axioms_doc_dir} 不存在")
        return None
        
    # 创建数据集目录
    
    print(f"处理 {len(subsumption_list)} 条子集关系记录...")
    for idx, item in enumerate(tqdm(subsumption_list)):
        sub_class = item['sub_verbalization']
        super_class = item['super_verbalization']
        conclusion_owl = f"SubClassOf(<{item['sub_class']}> <{item['super_class']}>)"
        
        # 构建查询
        query_id = f"{idx}"
        question = f"{sub_class} is a subclass of {super_class}"
        reasoning = "N/A"
        gold_answer = "N/A"
        
        # 证明中的公理作为golden_ids
        golden_ids = []
        justification_ids = []
        for justification_id in item['justifications']:
            just_k = [f"{axiom_id.split('_')[1]}" for axiom_id in justification_id]
            justification_ids.append(just_k)
            golden_ids += just_k
        # delete repeat golden_ids
        golden_ids = list(set(golden_ids))

        if not golden_ids:
            continue

        # 根据需求，将模块部分设置为["N/A"]
        exclude_ids = ["N/A"]
        golden_ids_long = ["N/A"]

        # 创建记录
        record = {
            "query": question,
            "reasoning": reasoning,
            "id": query_id,
            "exclude_ids": exclude_ids,
            "golden_ids_long": golden_ids_long,
            "golden_ids": golden_ids,
            "gold_answer": gold_answer,
            "justifications": justification_ids,
            "conclusion": conclusion_owl
            }

        dataset_records.append(record)

    # 保存为JSONL文件
    jsonl_path = os.path.join(output_dir, f"{ontology_name}_d{distance}.jsonl")
    with open(jsonl_path, 'w') as f:
        for record in dataset_records:
            f.write(json.dumps(record) + '\n')
    
    print(f"HuggingFace数据集已创建：{jsonl_path}")
    print(f"  - 共 {len(dataset_records)} 条记录")
    
    return jsonl_path


def build_rag_dataset(distance_list, owl_file_path: str, subsumption_dir: str, justification_dir: str, verbalization_mode: str = "standard"):
    """
    Build a RAG dataset from an ontology, its subsumptions and justifications.
    
    Args:
        owl_file_path: Path to the OWL file
        subsumption_dir: Directory containing subsumptions files
        justification_dir: Directory containing justification files
        verbalization_mode: Mode for verbalization (standard, iri, or random)
    """
    try:
        # Extract ontology name
        ontology_name = os.path.splitext(os.path.basename(owl_file_path))[0]
        print(f"Processing ontology: {ontology_name}")
        
        # Load ontology and create verbaliser
        ontology, verbaliser = load_ontology(owl_file_path, verbalization_mode=verbalization_mode)
        
        # Verbalize axioms
        axioms_dict = verbalize_axioms(ontology, verbaliser)
        
        if not axioms_dict:
            print("Warning: No axioms were verbalized. Check if the ontology contains logical axioms.")
            return {}, {}
        
        # Save axioms' natural language descriptions as text files
        if verbalization_mode == "standard":
            output_dir_doc = os.path.join(os.path.dirname(owl_file_path), "documents")
        else:
            output_dir_doc = os.path.join(os.path.dirname(owl_file_path), "documents_" + verbalization_mode)
        os.makedirs(output_dir_doc, exist_ok=True)
        save_axioms_as_text_files(axioms_dict, output_dir_doc, ontology_name)
        
        # Load subsumptions
        if not os.path.exists(subsumption_dir):
            print(f"Error: Subsumption directory {subsumption_dir} does not exist")
            return axioms_dict, {}
            
        subsumptions_dist = load_subsumptions(subsumption_dir)
        
        if not subsumptions_dist:
            print("Warning: No subsumptions found in the subsumption directory")
            return axioms_dict, {}
        
        # Build mapping from subsumptions to justifications
        print("Building subsumption to justification mapping...")
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        for distance, subsumptions in tqdm(subsumptions_dist.items()):
            if distance not in distance_list:
                continue
            subsumptions_list = []
            for idx, subsumption in enumerate(tqdm(subsumptions)):
                # Get subsumption details
                sub_class = subsumption[0]
                super_class = subsumption[1]
                
                # Get verbalizations for classes
                if sub_class in verbaliser.vocab:
                    sub_verbalization = verbaliser.vocab[sub_class]
                else:
                    sub_verbalization = sub_class.split('#')[-1] if '#' in sub_class else sub_class.split('/')[-1]
                
                if super_class in verbaliser.vocab:
                    super_verbalization = verbaliser.vocab[super_class]
                else:
                    super_verbalization = super_class.split('#')[-1] if '#' in super_class else super_class.split('/')[-1]
            
                # Process justifications
                just_dir = os.path.join(justification_dir, f"{ontology_name}_d{distance}", f"sub{idx+1}")
                justifications = []
                if not os.path.exists(just_dir):
                    skipped_count += 1
                    continue

                for just_file in os.listdir(just_dir):
                    justification_axioms = process_justification_file(os.path.join(just_dir, just_file), axioms_dict, force_find=True)
                    if justification_axioms:
                        justifications.append(justification_axioms)
                
                if not justifications:
                    skipped_count += 1
                    continue
                
                # Store the mapping
                subsumptions_list.append({
                    "sub_class": sub_class,
                    "super_class": super_class,
                    "distance": distance,
                    "justifications": justifications,
                    "module": ["N/A"],  # Set module to N/A as per requirement
                    "sub_verbalization": sub_verbalization,
                    "super_verbalization": super_verbalization,
                    "distance": distance
                })
                
                processed_count += 1
                
            # Print statistics
            print(f"Subsumption processing summary:")
            print(f"  - Total subsumptions: {len(subsumptions_dist)}")
            print(f"  - Processed: {processed_count}")
            print(f"  - Skipped: {skipped_count}")
        
            # Create HuggingFace dataset
            if verbalization_mode == "standard":
                output_dir_hf = os.path.join(os.path.dirname(owl_file_path), f"example")
            else:
                output_dir_hf = os.path.join(os.path.dirname(owl_file_path), f"example_{verbalization_mode}")
            os.makedirs(output_dir_hf, exist_ok=True)
            hf_dataset_dir = create_hf_dataset(subsumptions_list, output_dir_doc, ontology_name, output_dir_hf, distance)
            print(f"HuggingFace dataset created: {hf_dataset_dir}")
        
        return axioms_dict, subsumptions_list
        
    except Exception as e:
        print(f"Fatal error in build_rag_dataset: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}, {}


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="构建基于本体的RAG数据集，使用子类关系和证明")
    parser.add_argument("--owl", type=str, required=True, help="本体OWL文件路径")
    parser.add_argument("--subsumptions", type=str, required=True, help="包含子类关系的目录")
    parser.add_argument("--justifications", type=str, required=True, help="包含证明的目录")
    parser.add_argument("--verbalization_mode", "--vm", type=str, default="standard", 
                       choices=["standard", "random"], 
                       help="词汇化模式：standard-使用标签（默认，无标签使用IRI名称），random-使用随机生成的名称")

    args = parser.parse_args()
    
    build_rag_dataset(
        owl_file_path=args.owl,
        subsumption_dir=args.subsumptions,
        justification_dir=args.justifications,
        verbalization_mode=args.verbalization_mode,
    )
