import argparse
import json
import logging as log
import os
import sys
import toml
import yaml
from importlib.metadata import distribution
from pathlib import Path

from zoti_yaml import Module
from zoti_gen.handler import ProjHandler
import zoti_gen._main_utils as _mu

dist = distribution("zoti_gen")
parser = argparse.ArgumentParser(
    prog="zoti-gen",
    description="ZOTI template-based code generator.\n\n"
    "If input is received to the stdin it assumes it is the main module in jSON "
    "format and\nignores 'main'. Files passed to --input are loaded as auxiliary "
    "modules.",
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
    "-i", "--input", metavar="FILE", type=str, nargs='+',
    help="Input file(s).",
)
parser.add_argument(
    "-o", "--out", metavar="FILE",
    help="""Output code file. If not set, prints to stdout.""",
    type=argparse.FileType('w'),
    default=sys.stdout,
)
parser.add_argument(
    "-l", "--lib", type=str, nargs='+',
    help="""Path to loaded component libraries. Complements PYTHONPATH.""",
)
parser.add_argument(
    "-d", '--deps', metavar="FILE", nargs="?", default="none",
    help="Dump the resolved dependencies as a JSON file. If provided without\n"
    "argument creates a new file in the current folder.",
)
parser.add_argument(
    "-g", "--dump-graph", metavar="PATH", type=str,
    help="Dump a graph representing the code blocks structure.",
)
parser.add_argument(
    "--begin-block", metavar="STR", type=str,
    help="Formatted markup string to extract data at the beginning of a\n"
    "block. Main variable is {comp}.",
)
parser.add_argument(
    "--end-block", metavar="STR", type=str,
    help="Formatted markup string to extract data at the beginning of a\n"
    "block. Main variable is {comp}.",
)
parser.add_argument(
    "main",
    help="Name of the main module. If set to 'stdin' it assumes the main\n"
    "module is a JSON passed to the input stream.",
)
default_args = {
    "input": None,
    "deps": "none",
    "graph": None,
    "begin_block": None,
    "end_block": None,
}

# load configuration
args = parser.parse_args()
try:
    log.basicConfig(level=args.loglevel,
                    format='%(levelname)s: %(message)s', stream=sys.stderr)
    conf = _mu.load_config("zoti.gen", args, default_args)
    log.info(f"{conf}")

    modules = []
    try:
        preamble, doc = _mu.read_json_from_stdin()
        conf["main"] = preamble["module"]
        modules.append(Module(preamble, doc))
    except Exception:
        pass

    paths = [Path(p) for p in args.input] if args.input else []
    for path in paths:
        if path.suffix in [".yaml", ".yml"]:
            with open(path) as f:
                modules.append(Module(*yaml.load_all(f, Loader=yaml.Loader)))
        elif path.suffix in [".json"]:
            with open(path) as f:
                modules.append(Module(*json.load(f)))
        else:
            log.info(f"Ignoring file '{path}'")
    main = conf["main"]

    if conf["lib"]:
        sys.path += conf["lib"]

    gen = ProjHandler(main, modules,
                      annotation=(conf["begin_block"], conf["end_block"]))
    gen.parse()
    gen.resolve()

    for cp in gen.decls:
        block = gen.get(cp).code
        if block:
            args.out.write(block)
            args.out.write("\n\n")
    log.info(f"  * Dumped code file '{args.out.name}'")

    if conf["deps"] != "none":
        dfile = (Path(f"{main}.deps.json")
                 if conf["deps"] is None else Path(conf["deps"]))
        with open(dfile, "w") as f:
            json.dump(gen.requs.as_dict(), f)
            log.info(f"  * Dumped dependency spec '{f.name}'")

    if conf["dump_graph"]:
        gen.dump_graph(Path(conf["dump_graph"]).joinpath(
            main).with_suffix(".genspec.dot"))
except Exception as e:
    Path(args.out.name).unlink(missing_ok=True)
    raise e
