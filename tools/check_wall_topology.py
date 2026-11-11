"""Repeatable synthetic join/split audit; never reads or saves user plans."""
import argparse
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=2000)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    from survey.plan_geometry import normalize_segments
    from tests.test_wall_topology_invariants import random_wall_graph,signature
    start = perf_counter()
    for seed in range(args.cases):
        graph = random_wall_graph(seed)
        first,sources = normalize_segments(graph,with_sources=True)
        second = normalize_segments(first)
        expected = signature(first)
        assert expected == signature(second), ('repeated normalization',seed)
        assert len(expected) == len(set(expected)), ('duplicate',seed)
        assert all(s and set(s) <= set(range(len(graph))) for s in sources), ('source mapping',seed)
        random.Random(seed+10000).shuffle(graph)
        assert expected == signature(normalize_segments(graph)), ('input order',seed)
    result = dict(cases=args.cases,seconds=perf_counter()-start,failures=0,
                  checks=['stable repeated normalization','no identical physical duplicates','source mapping','input order independence'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__ == '__main__':
    main()
