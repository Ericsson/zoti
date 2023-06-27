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
from zoti_gen.builder import Builder
import zoti_gen.io as io
import zoti_gen._main_utils as _mu

dist = distribution("zoti_gen")
parser = argparse.ArgumentParser(
    prog="zoti-gen",
    description="ZOTI template-based code generator.\n\n"
    "If input is received to the stdin it assumes it is the main module in jSON "
    "format and\nignores --main. Files passed to --input are loaded as auxiliary "
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
    help="Input file(s). Accepts only '.yml', '.yaml' and '.json' files.\n"
    "Other file types are ignored.",
)
parser.add_argument(
    "-m", "--main", metavar="MODULE", type=str,
    help="Name of the main module. If not specified it is assumes to be:\n"
    "1) the JSON stream passed to stdin (if it is the case); or\n"
    "2) the first file in the input list."
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
action = parser.add_argument_group('debugging')
action.add_argument(
    "--begin-block", metavar="STR", type=str,
    help="Formatted markup string to extract data at the beginning of a\n"
    "block. Main variable is {comp}.",
)
action.add_argument(
    "--end-block", metavar="STR", type=str,
    help="Formatted markup string to extract data at the end of a\n"
    "block. Main variable is {comp}.",
)
action.add_argument(
    "--dump-graph", action="store_true",
    help="Dump a graph representing the code blocks structure.",
)
action.add_argument(
    "--dump-yaml", action="store_true",
    help="Dump the resolved blocks structure in a yaml file.",
)
action.add_argument(
    "--dump-path", metavar="PATH", type=str, default=".",
    help="""Path where debug byproducts are dumped. Default is '.' """,
)
action.add_argument(
    "--info-keys", action="store_true",
    help="""Print info keys for piping from ZOTI-YAML and exit""",
)
default_args = {
    "input": None,
    "deps": "none",
    "dump_path": ".",
    "begin_block": None,
    "end_block": None,
}

# load configuration
args = parser.parse_args()
if args.info_keys:
    print(io.print_zoti_yaml_keys())
    exit(0)

try:
    log.basicConfig(level=args.loglevel,
                    format='%(levelname)s: %(message)s', stream=sys.stderr)
    conf = _mu.load_config("zoti.gen", args, default_args)
    log.info(f"{conf}")

    modules = []
    try:
        modules.append(Module(*_mu.read_json_from_stdin()))
    except Exception:
        pass
    paths = [Path(p) for p in args.input] if args.input else []
    for path in paths:
        if path.suffix in [".yaml", ".yml"]:
            with open(path) as f:
                modules.append(Module(*yaml.load_all(f, Loader=io.ZotiGenLoader)))
        elif path.suffix in [".json"]:
            with open(path) as f:
                modules.append(Module(*json.load(f)))
        else:
            log.info(f"Ignoring file '{path}'")
    main = conf["main"] if conf["main"] else modules[0].preamble["module"]

    if conf["lib"]:
        sys.path += conf["lib"]

    gen = Builder(main, modules,
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
        io.dump_graph(gen, Path(conf["dump_path"]).joinpath(main).with_suffix(".resolved.dot"))
    if conf["dump_yaml"]:
        io.dump_yaml(gen, Path(conf["dump_path"]).joinpath(main).with_suffix(".resolved.yaml"))
except Exception as e:
    Path(args.out.name).unlink(missing_ok=True)
    raise e
