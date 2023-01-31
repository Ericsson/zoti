import argparse
import json
import logging as log
import pickle
import sys
from importlib.metadata import distribution
from pathlib import Path

import yaml

import zoti_ftn.backend.c as c
import zoti_ftn.lang as lang
import zoti_ftn.tokens as tok

dist = distribution("zoti_ftn")


def _write_to_more(path, docs):
    if len(docs) == 1:
        with open(path.with_suffix(".yaml"), "w") as f:
            yaml.dump_all(docs[0], f, default_flow_style=None)
    else:
        for doc, out in zip(
                docs,
                [path.with_stem(f"{path.stem}_{i}").with_suffix(".yaml")
                 for i in range(len(docs))]):
            with open(out, "w") as f:
                yaml.dump_all(doc, f, default_flow_style=None)


def parse(args):
    # print(args.i, args.o)
    docs = lang.load_file(args.i)
    yaml.dump_all(docs[0], sys.stdout, default_flow_style=None)
    
    # if args.o.name != "<stdout>":
    #     _write_to_more(Path(args.o.name), docs)
    # else:
    #     for doc in docs:
    #         yaml.dump_all(doc, sys.stdout, default_flow_style=None)


def types(args):
    raise NotImplementedError("CLI tool deprecated. Use the API instead")
    module = c  # TODO: choices
    paths = [p for g in args.file for p in sorted(Path(".").glob(g))]
    opath = Path(args.out)

    if paths[0].suffix == ".p":
        ftn = pickle.load(paths[0])
    else:
        for path in paths:
            if path.suffix == ".ftn":
                with open(path) as f:
                    docs = lang.load_file(f)
                _write_to_more(path, docs)
        paths = (
            [p for path in paths
             for p in sorted(path.parent.glob(f"{path.stem}*.yaml"))
             if path.suffix == ".ftn"]
            + [p for p in paths if path.suffix != ".ftn"])
        # print(paths)
        docs = []
        for path in paths:
            if path.suffix in [".yml", ".yaml"]:
                with open(path) as f:
                    doc = yaml.load_all(f, Loader=yaml.Loader)
                    docs.append(list(doc))
            elif path.suffix in [".json"]:
                with open(path) as f:
                    docs.append(json.load(f))
            else:
                log.warning(f"Unrecognized file type {path.as_posix()}. Igoring...")
        ftn = module.FtnDb({doc[0]["module"]: doc[1][tok.ATTR_ENTRIES] for doc in docs})

    types = args.type if args.type else [
        f"{mod}.{name}" for mod, doc in ftn._srcs.items() for name in doc.keys()]
    # print(types)
    for ty in types:
        _ = ftn.get(ty)
    # print(ftn.loaded_types())

    if args.raw_pickle:
        dumppath = opath.with_suffix(".raw.p")
        with open(dumppath, "wb") as f:
            pickle.dump(ftn, f)
        return

    if args.deps:
        tydeps = ftn.type_dependency_graph()
        doc = {
            "lib-deps": ftn.requirements(),
            "type-deps": {"nodes": list(tydeps.nodes()),
                          "edges": [[u, v] for u, v in tydeps.edges()]
                          }
        }
        with open(args.deps, "w") as f:
            yaml.dump(doc, f, default_flow_style=None)

    
    # TODO: entries


parser = argparse.ArgumentParser(
    prog="zoti-ftn",
    description="Flexible Type Notation tool, implemented in Python",
    formatter_class=argparse.RawTextHelpFormatter,
)
parser.add_argument("--version", action="version", version=" %(prog)s-" + dist.version)
parser.add_argument(
    "--verbose",
    help="prints additional info statements",
    action="store_const",
    dest="loglevelStdout",
    const=log.INFO,
    default=log.WARNING,
)

subparsers = parser.add_subparsers(
    help="Sub-commands. Type in command name and -h for more help."
)
parser_parse = subparsers.add_parser(
    'parse',
    help="Command that parses FTN and dumps ZOTI-YAML."
)
parser_parse.add_argument(
    '-o',
    help="Output file. If not specified writes to stdout.",
    type=argparse.FileType('w'),
    default=sys.stdout
)

parser_parse.add_argument(
    'i',
    help="Input file. If not specified reads from stdin.",
    type=argparse.FileType('r'),
    default=sys.stdin
)
parser_parse.set_defaults(func=parse)

parser_type = subparsers.add_parser(
    'types',
    help="Command that takes care of type code generation.",
    formatter_class=argparse.RawTextHelpFormatter,
)
parser_type.add_argument(
    "-l",
    "--lang",
    help="""Language of the generated type code.""",
    type=str,
    choices=["c"],
    default="c"
)
parser_type.add_argument(
    "-o",
    "--out",
    help="""File where the processed types will be.""",
    metavar="PATH",
    type=str,
    default="."
)
parser_type.add_argument(
    "-d",
    "--deps",
    type=str,
    metavar="FILE",
    help=("Dumps dependency information in a separate file")
)
parser_type.add_argument(
    "-p",
    "--raw-pickle",
    help=("Dumps the current FTN handler into a binary file with raw data.\n"
          "TODO/BUG: cannot pickle due to implementation of handler."),
    action="store_true"
)
parser_type.add_argument(
    "-t",
    "--type",
    help="Select types. If not specified, all types will be processed.\n"
    "OBS! Type dependencies are not considered.",
    type=str,
    nargs='+',
)
parser_type.add_argument(
    "-e",
    "--entry",
    help="Select entries. If not specified, all entries will be featured.\n"
    "TODO: not implemented yet. Only API is used to generate code.",
    type=str,
    nargs='+',
)

parser_type.add_argument(
    "file",
    help=(
        "List of input files (globs). Extensions determine the input format:\n"
        + " - *.ftn: specification in the FTN language;\n"
        + " - *.yaml|*.json: specification in a serialization format;\n"
        + " - *.raw.p: raw unparsed binary data"
    ),
    type=str,
    nargs='+',
)
parser_type.set_defaults(func=types)

args = parser.parse_args()
args.func(args)
