from dumputils import SpecDumper
import sys
import yaml
import json
import pathlib
import argparse
import logging as log
from pathlib import Path
from importlib.metadata import distribution

import zoti_graph as graph
import zoti_graph.script as tran
import zoti_graph.genny as genny
import zoti_graph.genny.sanity as sanity
import zoti_graph.genny.translib as agnostic
import zoti_ftn.backend.c as ftn

sys.path.insert(0, pathlib.Path(__file__).parent.resolve())
import artifacts
import translib as target

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

if gpath.suffixes == [".raw", ".json"]:
    with open(gpath) as f:
        G = graph.from_raw(f, version=dist_zoti_graph.version)
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
        dump_graphviz={
            "port_info": lambda p: f"{p.port_type.__class__.__name__},{p.data_type.uid}",
            "node_info": lambda p: ",".join([k for k in p.mark.keys()]),
        } if args.debug else None,
    ),
    tran.TransSpec(
        target.prepare_platform_ports,
        dump_title="tran_2_prepare_platform_ports",
        dump_graphviz={
            # "port_info": lambda p: f"{p.data_type['type']}",
            "port_info": lambda p: ",".join([f"{k}-{v}" for k, v in p.mark.items()]),
        } if args.debug else None,
    ),
    tran.TransSpec(
        target.expand_actors,
        dump_title="tran_3_expand_actors",
        dump_nodes=debug,
        dump_graphviz={
            "node_info": lambda p: ",".join([k for k in p.mark.keys()]),
        } if args.debug else None,
    ),
    tran.TransSpec(
        agnostic.flatten,
        dump_title="tran_4_flatten",
        dump_graphviz=debug,
    ),
    tran.TransSpec(
        target.prepare_side_ports,
        dump_title="tran_5_prepare_side_ports",
        dump_graphviz={
            "node_info": lambda n: (
                str(n.mark) if isinstance(n, genny.CompositeNode)
                else ",".join([k for k in n.mark.keys()])),
            "port_info": lambda p: p.kind.name,
        } if args.debug else None,
    ),
    tran.TransSpec(
        agnostic.fuse_actors,
        dump_title="tran_6_fuse_actors",
        dump_graphviz={
            "NODE_info": lambda p: ",".join([k for k in p.mark.keys()]),
        } if args.debug else None,
    ),
    tran.TransSpec(
        target.prepare_intermediate_ports,
        dump_title="tran_7_prepare_intermediate_ports",
        dump_graphviz={
            "node_info": lambda n: (
                str(n.mark) if isinstance(n, genny.CompositeNode)
                else ",".join([k for k in n.mark.keys()])),
            # "port_info": lambda p: ",".join([k for k in p.mark.keys()]),
            "port_info": lambda p: type(p).__name__,
        } if args.debug else None,
    ),
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
