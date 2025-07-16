import os
import argparse
import json
import sys
from tqdm import tqdm

# 添加BRIGHT目录到路径中以便导入retrievers模块
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'BRIGHT'))
from retrievers import RETRIEVAL_FUNCS, calculate_retrieval_metrics
from datasets import load_dataset

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', type=str, required=True)
    parser.add_argument('--random', action='store_true')
    parser.add_argument('--depth', type=int, required=True)
    parser.add_argument('--model', type=str, required=True,
                        choices=['bm25','cohere','e5','google','grit','inst-l','inst-xl',
                                 'openai','qwen','qwen2','sbert','sf','voyage','bge'])
    parser.add_argument('--long_context', action='store_true')
    parser.add_argument('--query_max_length', type=int, default=-1)
    parser.add_argument('--doc_max_length', type=int, default=-1)
    parser.add_argument('--encode_batch_size', type=int, default=-1)
    parser.add_argument('--output_dir', type=str, default='outputs')
    parser.add_argument('--cache_dir', type=str, default=os.path.join(BASE_DIR, 'cache'))
    parser.add_argument('--checkpoint', type=str, default=None)
    parser.add_argument('--key', type=str, default=None)
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--ignore_cache', action='store_true')
    parser.add_argument('--config_dir', type=str, default='configs')
    parser.add_argument('--use_exclude_ids', type = bool, default = False, help="whether use exclude_ids")
    args = parser.parse_args()

    if args.random:
        examples_path = os.path.join(f'{BASE_DIR}/data/example_random', f"{args.task}_d{args.depth}.jsonl")
        args.task += '_random'
    else:
        examples_path = os.path.join(f'{BASE_DIR}/data/example', f"{args.task}_d{args.depth}.jsonl")
    assert os.path.isfile(examples_path)

    args.output_dir = os.path.join(args.output_dir,f"{args.task}_d{str(args.depth)}_{args.model}_long_{args.long_context}")
    if not os.path.isdir(args.output_dir):
        os.makedirs(args.output_dir)
    score_file_path = os.path.join(args.output_dir,f'score.json')
    
    # 从本地example目录加载
    with open(examples_path) as f:
        examples = [json.loads(line) for line in f]

    # 从本地documents目录加载文档
    doc_name = args.task
    documents_path = os.path.join(f'{BASE_DIR}/data/documents', 
                                 f"{doc_name}.jsonl")
    assert os.path.isfile(documents_path)
    with open(documents_path) as f:
        doc_pairs = [json.loads(line) for line in f]

    # 处理文档
    doc_ids = []
    documents = []
    for dp in doc_pairs:
        doc_ids.append(dp['id'])
        documents.append(dp['content'])

    if not os.path.isfile(score_file_path):
        with open(os.path.join(args.config_dir,args.model,f"ont.json")) as f:
            config = json.load(f) 
        if not os.path.isdir(args.output_dir):
            os.makedirs(args.output_dir)

        queries = []
        query_ids = []
        excluded_ids = {}
        for e in examples:
            queries.append(e["query"])
            query_ids.append(e['id'])
            if args.use_exclude_ids:
                excluded_ids[e['id']] = e['exclude_ids']
                overlap = set(e['exclude_ids']).intersection(set(e['golden_ids']))
                assert len(overlap)==0
            else:
                excluded_ids[e['id']] = ["N/A"]
        assert len(queries)==len(query_ids), f"{len(queries)}, {len(query_ids)}"
        if not os.path.isdir(os.path.join(args.cache_dir, 'doc_ids')):
            os.makedirs(os.path.join(args.cache_dir, 'doc_ids'))
        if os.path.isfile(os.path.join(args.cache_dir,'doc_ids',f"{args.task}_d{args.depth}.json")):
            with open(os.path.join(args.cache_dir,'doc_ids',f"{args.task}_d{args.depth}.json")) as f:
                cached_doc_ids = json.load(f)
            for id1,id2 in zip(cached_doc_ids,doc_ids):
                assert id1==id2
        else:
            with open(os.path.join(args.cache_dir,'doc_ids',f"{args.task}_{args.long_context}.json"),'w') as f:
                json.dump(doc_ids,f,indent=2)
        assert len(doc_ids)==len(documents), f"{len(doc_ids)}, {len(documents)}"

        print(f"{len(queries)} queries")
        print(f"{len(documents)} documents")
        if args.debug:
            documents = documents[:30]
            doc_paths = doc_ids[:30]
        kwargs = {}
        if args.query_max_length>0:
            kwargs = {'query_max_length': args.query_max_length}
        if args.doc_max_length>0:
            kwargs.update({'doc_max_length': args.doc_max_length})
        if args.encode_batch_size>0:
            kwargs.update({'batch_size': args.encode_batch_size})
        if args.key is not None:
            kwargs.update({'key': args.key})
        if args.ignore_cache:
            kwargs.update({'ignore_cache': args.ignore_cache})
        scores = RETRIEVAL_FUNCS[args.model](
            queries=queries, query_ids=query_ids, documents=documents, excluded_ids=excluded_ids,
            instructions=config['instructions_long'] if args.long_context else config['instructions'],
            doc_ids=doc_ids, task=args.task, cache_dir=args.cache_dir, long_context=args.long_context,
            model_id=args.model, checkpoint= args.checkpoint, **kwargs
        )
        with open(score_file_path,'w') as f:
            json.dump(scores,f,indent=2)
    else:
        with open(score_file_path) as f:
            scores = json.load(f)
        print(score_file_path,'exists')
    if args.long_context:
        key = 'golden_ids_long'
    else:
        key = 'golden_ids'
    ground_truth = {}
    for e in tqdm(examples):
        ground_truth[e['id']] = {}
        for gid in e[key]:
            ground_truth[e['id']][gid] = 1
        if args.use_exclude_ids:
            for did in e['exclude_ids']:
                assert not did in scores[e['id']]
                assert not did in ground_truth[e['id']]

    print(args.output_dir)
    results = calculate_retrieval_metrics(results=scores, qrels=ground_truth)
    with open(os.path.join(args.output_dir, 'results.json'), 'w') as f:
        json.dump(results, f, indent=2)
