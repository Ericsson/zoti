from dumputils import SpecDumper
import sys
import yaml
import json
import pathlib
import argparse
import logging as log
from pathlib import Path
from importlib.metadata import distribution

import artifacts
import translib as target

import zoti_graph as graph
import zoti_graph.sanity as sanity
import zoti_ftn.backend.c as ftn
import zoti_tran as tran
import zoti_tran.translib as agnostic

sys.path.insert(0, pathlib.Path(__file__).parent.resolve())


dist_zoti_graph = distribution("zoti_graph")
dist_zoti_ftn = distribution("zoti_ftn")

parser = argparse.ArgumentParser()
parser.add_argument(
    "--verbose", action="store_const",
    dest="loglevel", const=log.INFO, default=log.WARNING,
    help="prints additional info statements",
)
parser.add_argument("-g", "--graph", metavar="FILE", type=str, required=True)
parser.add_argument("-f", "--ftn", type=str, required=True)
parser.add_argument("-p", "--plots", type=str, default=".")
parser.add_argument("-o", "--output", type=str, default=".")
parser.add_argument(      "--typeshdr", type=str, required=True)
parser.add_argument(      "--depl", type=str, required=True)
parser.add_argument("--debug", action='store_true')
args = parser.parse_args()

log.basicConfig(level=args.loglevel,
                format='%(levelname)s: %(message)s', stream=sys.stderr)

gpath = Path(args.graph)
fpath = Path(args.ftn)

if gpath.suffixes == [".raw", ".yaml"]:
    with open(gpath) as f:
        G = graph.from_raw_yaml(f, version=dist_zoti_graph.version)
else:
    raise NotImplementedError(f"Cannot handle {gpath}")


if fpath.suffix == ".yaml":
    with open(fpath) as f:
        T = ftn.FtnDb(yaml.load(f, Loader=yaml.Loader))
else:
    raise NotImplementedError(f"Cannot handle {gpath}")


################ END NOISE. BEGIN SCRIPT ######################

debug = {} if args.debug else None
script = tran.Script(G, T, dump_prefix=args.plots)

script.sanity([
    sanity.port_dangling,
    sanity.node_platform_hierarchy,
    sanity.node_actor_hierarchy,
    sanity.node_actor_consistency,
    sanity.node_kernel_hierarchy,
    sanity.edge_direction,
    sanity.edge_hierarchy,
    sanity.edge_sibling_kind,
])

script.transform([
    tran.TransSpec(
        target.port_inference,
        dump_title="tran_1_port_inference",
        dump_nodes=debug,
        dump_graph={
            "port_info": lambda p: f"{p.port_type.__class__.__name__},{p.data_type['type'].__class__.__name__}",
            "leaf_info": lambda p: ",".join([k for k in p.mark.keys()]),
        } if args.debug else None,
    ),
    tran.TransSpec(
        target.receiver_types,
        dump_title="tran_2_receiver_types",
        dump_graph={
            "port_info": lambda p: f"{p.data_type['type']}",
            # "port_info": lambda p: p.dir.name,
            # "edge_info": lambda e: e.kind.name,
        } if args.debug else None,
    ),
    tran.TransSpec(
        target.expand_actors,
        dump_title="tran_3_expand_actors",
        dump_nodes=debug,
        dump_graph={
            "composite_info": lambda p: ",".join([k for k in p.mark.keys()]),
            "leaf_info": lambda p: ",".join([k for k in p.mark.keys()]),
        } if args.debug else None,
    ),
    tran.TransSpec(
        agnostic.flatten,
        dump_title="tran_4_flatten",
        dump_graph=debug,
    ),
    tran.TransSpec(
        agnostic.fuse_actors,
        dump_title="tran_5_fuse_actors",
        dump_graph={
            "edge_info": lambda e: str(e.kind.name),
            "composite_info": lambda p: ",".join([k for k in p.mark.keys()]),
        } if args.debug else None,
    ),
    tran.TransSpec(
        target.clean_ports,
        dump_title="tran_6_clean_ports",
        dump_graph={
            "composite_info": lambda c: str(c.mark),
            "leaf_info": lambda p: ",".join([k for k in p.mark.keys()]),
            "port_info": lambda p: p.dir.name,
            "edge_info": lambda e: e.kind.name,
        } if args.debug else None,
    ),
    # tran.TransSpec(
    #     target.separate_reactions,
    #     dump_title="tran_7_separate_reactions",
    #     dump_graph={
    #         "composite_info": lambda c: str(c.mark),
    #         "port_info": lambda p: ",".join([k for k in p.mark.keys()]),
    #         # "port_info": lambda p: p.dir.name,
    #         # "edge_info": lambda e: e.kind.name,
    #     } if args.debug else None,
    # ),
    tran.TransSpec(artifacts.typedefs),
    tran.TransSpec(artifacts.genspec),
    tran.TransSpec(artifacts.gendepl),
])

# assert False

for node, spec in script.genspec.items():
    with open(Path(args.output).joinpath(node).with_suffix(".zoc"), "w") as f:
        yaml.dump_all(spec, f, Dumper=SpecDumper, default_flow_style=None)
        log.info(f"  * Dumped genspec '{f.name}'")

for fname, text in script.typedefs.items():
    with open(Path(args.typeshdr).with_name(fname), "w") as f:
        f.write(text)
        log.info(f"  * Dumped typedefs '{f.name}'")

with open(Path(args.depl), "w") as f:
    f.write(json.dumps(script.gendepl, indent=2))
    log.info(f"  * Dumped deploy spec '{f.name}'")