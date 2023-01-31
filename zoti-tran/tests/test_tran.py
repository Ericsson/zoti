import os
import sys
import yaml
from pathlib import Path

sys.path.insert(0, "src")
from zoti_graph import parse
from zoti_tran.script import Script, TransSpec
import zoti_tran.sanitylib as sanity
import zoti_tran.translib as rule

def test_scenario1() -> None:

    with open("tests/inputs/graph1.yaml") as f:
        G = parse(*yaml.load_all(f, Loader=yaml.Loader))

    print("")
    tran = Script(G)

    tran.sanity(
        port_rules=[
            sanity.port_dangling,
        ],
        node_rules=[
            sanity.node_platform_hierarchy,
            sanity.node_actor_hierarchy,
            sanity.node_actor_consistency,
            sanity.node_kernel_hierarchy,
        ],
        edge_rules=[
            sanity.edge_direction,
            sanity.edge_hierarchy,
            sanity.edge_sibling_kind,
        ],
    )

    tran.transform([
        TransSpec(
            rule.flatten,
            dump_tree={},
            dump_graph={},
        ),
        TransSpec(
            rule.fuse_actors,
            dump_tree={},
            dump_graph={
                "edge_info": lambda e: str(e.kind),
            },
        ),
    ])
    try:
        pass
    except Exception as e:
        raise e
    finally:
        for path in Path().glob("*.dot"):
            os.remove(path)
