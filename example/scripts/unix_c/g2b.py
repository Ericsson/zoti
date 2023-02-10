import sys
import yaml
import pathlib
import argparse
import logging as log
from pathlib import Path
from importlib.metadata import distribution

import zoti_graph as graph
import zoti_graph.sanity as sanity
import zoti_ftn.backend.c as ftn
import zoti_tran as tran
import zoti_tran.translib as agnostic

sys.path.insert(0, pathlib.Path(__file__).parent.resolve())

import translib as target
import genspec
from dumputils import SpecDumper


dist_zoti_graph = distribution("zoti_graph")
dist_zoti_ftn = distribution("zoti_ftn")

parser = argparse.ArgumentParser()
parser.add_argument(
    "--verbose", action="store_const",
    dest="loglevel", const=log.INFO, default=log.WARNING,
    help="prints additional info statements",
)
parser.add_argument("-g", "--graph", metavar="FILE", type=str, required=True)
parser.add_argument("-f", "--ftn", nargs='+', required=True)
parser.add_argument("-p", "--prefix", type=str, default=".")
parser.add_argument("-o", "--output", type=str, default=".")
parser.add_argument("-c", "--code", type=str, default=".")
parser.add_argument("--debug", action='store_true')
args = parser.parse_args()

log.basicConfig(level=args.loglevel,
                format='%(levelname)s: %(message)s', stream=sys.stderr)

gpath = Path(args.graph)
# fpaths = Path().glob(args.ftn)
fpaths = [Path(p) for p in args.ftn]

if gpath.suffixes == [".raw",".yaml"]:
    with open(gpath) as f:
        G = graph.from_raw_yaml(f, version=dist_zoti_graph.version)
else:
    raise NotImplementedError(f"Cannot handle {gpath}")

ftn_srcs = []
for fpath in fpaths:
    if fpath.suffix in [".yml", ".yaml"]:
        with open(fpath) as f:
            doc = yaml.load_all(f, Loader=yaml.Loader)
            ftn_srcs.append(list(doc))
    else:
        raise NotImplementedError(f"Cannot handle {fpath}")

T = ftn.FtnDb({doc[0]["module"]: doc[1]["entries"] for doc in ftn_srcs})


################ END NOISE. BEGIN SCRIPT ######################

debug = {} if args.debug else None
script = tran.Script(G, T, dump_prefix=args.prefix)

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
        dump_nodes=debug,
        dump_graph={
            "port_info": lambda p: f"{p.port_type.__class__.__name__},{p.data_type['type'].__class__.__name__}",
            "leaf_info": lambda p: ",".join([k for k in p.mark.keys()]),
        } if args.debug else None,
    ),
    tran.TransSpec(
        target.expand_actors,
        dump_nodes=debug,
        dump_graph={
            "composite_info": lambda p: ",".join([k for k in p.mark.keys()]),
            "leaf_info": lambda p: ",".join([k for k in p.mark.keys()]),
        } if args.debug else None,
    ),
    tran.TransSpec(
        agnostic.flatten,
        # dump_tree={},
        dump_graph=debug,
    ),
    tran.TransSpec(
        agnostic.fuse_actors,
        # dump_tree={},
        dump_graph={
            "edge_info": lambda e: str(e.kind.name),
            "composite_info": lambda p: ",".join([k for k in p.mark.keys()]),
        } if args.debug else None,
    ),
    tran.TransSpec(
        target.clean_ports,
        dump_graph={
            "composite_info": lambda c: str(c.mark),
            "leaf_info": lambda p: ",".join([k for k in p.mark.keys()]),
            "port_info": lambda p: p.dir.name,
            "edge_info": lambda e: e.kind.name,
        } if args.debug else None,
    ),
    tran.TransSpec(
        target.separate_reactions,
        dump_graph={
            "composite_info": lambda c: str(c.mark),
            "port_info": lambda p: ",".join([k for k in p.mark.keys()]),
            # "port_info": lambda p: p.dir.name,
            # "edge_info": lambda e: e.kind.name,
        } if args.debug else None,
    ),
    tran.TransSpec(genspec.typedefs),
    tran.TransSpec(genspec.genspec),
])

for node, spec in script.genspec.items():
    with open(Path(args.output).joinpath(node).with_suffix(".zoc"), "w") as f:
        yaml.dump_all(spec, f, Dumper=SpecDumper, default_flow_style=None)
        log.info(f"  * Dumped genspec '{f.name}'")

for fname, text in script.typedefs.items():
    with open(Path(args.code).joinpath(fname), "w") as f:
        f.write(text)
        log.info(f"  * Dumped typedefs '{f.name}'")
