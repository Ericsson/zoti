import argparse
import json
import logging as log
import pickle
import sys
import os
import toml
import yaml
from importlib.metadata import distribution
from pathlib import Path

import zoti_graph.io as io
import zoti_graph._main_utils as _mu
from zoti_graph.parser import parse


dist = distribution("zoti_graph")
parser = argparse.ArgumentParser(
    prog="zoti-graph",
    description="ZOTI application graph representation, implemented in Python.\n\n"
    "The following formats are available as inputs/outputs:\n"
    " - *.yaml|*.json: _only inputs_, parsed and schema-validated;\n"
    " - *.raw.yaml: raw format, compatible with any ZOTI graph representer"
    f" version ^{dist.version};\n"
    " - *.raw.p: raw binary data, compatible with only this representer.",
    formatter_class=argparse.RawTextHelpFormatter,
)
parser.add_argument("--version", action="version",
                    version=" %(prog)s-" + dist.version)
parser.add_argument(
    "--verbose", action="store_const",
    dest="loglevel", const=log.INFO, default=log.WARNING,
    help="prints additional info statements",
)
parser.add_argument(
    "-i", "--input", metavar="FILE",
    help="If not specified reads the content of a '.json' file from stdin.",
    type=argparse.FileType('r'),
    default=sys.stdin,
)
parser.add_argument(
    "-o", "--out", metavar="FILE",
    help="""If not specified writes output to stdout as '.raw.yaml'.""",
    type=argparse.FileType('w'),
    default=sys.stdout,
)
action = parser.add_argument_group('debugging')
action.add_argument(
    "--dump-info", action="store_true",
    help="""Dumps a text file with info on all nodes in the graph""",
)
action.add_argument(
    "-g", "--dump-graph", action="store_true",
    help=("Draws a dot file representing the graph structure of the loaded."),
)
action.add_argument(
    "-t", "--dump-tree", action="store_true",
    help=("Draws a dot file representing the hierarchy of the loaded application."),
)
action.add_argument(
    "--dump-args", type=str, metavar="DICT",
    help="""Arguments passed to --dump-graph and --dump-tree commands as key-value\n"""
    """pairs. Only specified via 'zoticonf.toml'""",
)
action.add_argument(
    "--dump-out", type=str, metavar="PATH",
    help="""Path where debug byproducts are dumped. Default is '.' """,
)
default_args = {
    "out": None,
    "args": {}
}

# Parsing and forming arguments
args = parser.parse_args()
try:
    log.basicConfig(level=args.loglevel,
                    format='%(levelname)s: %(message)s', stream=sys.stderr)
    conf = _mu.load_config("zoti.graph", args, default_args)
    log.info(f"{conf}")
    dpath = Path(conf["dump_out"]) if conf["dump_out"] else Path()
    # dumpargs = yaml.load(conf['args'], Loader=yaml.SafeLoader)
    dumpargs = conf['args']
    assert isinstance(dumpargs, dict)
    # if dumpargs:
    #     log.info("Drawing arguments found:", dumpargs)

    # Reading input
    i_ext = ("".join(Path(args.input.name).suffixes)
             if not "stdin" in args.input.name else ".json")
    name = (Path(args.input.name).name.split(".")[0]
            if not "stdin" in args.input.name else None)
    if i_ext in [".yaml", ".yml"]:
        log.info(f"Parsing graph from YAML: {args.input.name}")
        G = parse(*yaml.load_all(args.input, Loader=yaml.Loader))
    elif i_ext in [".json"]:
        log.info(f"Parsing graph from JSON: {args.input.name}")
        G = parse(*json.load(args.input))
    elif i_ext in [".raw.yaml", ".raw.yml"]:
        log.info(f"Loading graph from raw YAML: {args.input.name}")
        G = io.from_raw_yaml(args.input, dist.version)
    elif i_ext in [".raw.p", ".raw.pickle"]:
        log.info(f"Loading graph from raw pickle: {args.input.name}")
        G = pickle.load(args.input)
    else:
        raise ValueError(f"Cannot recognize extension of {args.input.name}")

    # Dumping debug files
    if conf['dump_info']:
        with open(dpath.joinpath(f"{name}_info.txt"), "w") as f:
            io.dump_node_info(G, f)
    if conf['dump_graph']:
        with open(dpath.joinpath(f"{name}_graph.dot"), "w") as f:
            io.draw_graph(G, f, **dumpargs)
    if conf['dump_tree']:
        with open(dpath.joinpath(f"{name}_tree.dot"), "w") as f:
            io.draw_tree(G, f, **dumpargs)

    # Dumping output
    o_ext = ("".join(Path(args.out.name).suffixes)
             if not "stdin" in args.out.name else ".raw.yaml")

    if o_ext in [".raw.yaml", ".raw.yml"]:
        io.dump_raw_yaml(G, args.out)
    elif o_ext in [".raw.pickle", ".raw.p"]:
        pickle.dump(G, args.out,)
    else:
        raise ValueError(f"Unknown output format for {conf['out']}")
    log.info("Done")
except Exception as e:
    Path(args.out.name).unlink(missing_ok=True)
    raise e
