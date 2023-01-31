import argparse
import json
import logging as log
import pickle
import sys
import yaml
from pathlib import Path

from zoti_yaml import __version__
from zoti_yaml import Project
from zoti_yaml.dumper import ZotiDumper, ZotiEncoder
from zoti_yaml.core import ATTR_MODULE, ATTR_PATH
import zoti_yaml._main_utils as _mu


parser = argparse.ArgumentParser(
    prog="zoti-yaml",
    description="Small formatter for ZOTI input files.",
    formatter_class=argparse.RawTextHelpFormatter,
)
parser.add_argument(
    "--version", action="version", version=" %(prog)s-" + __version__
)
parser.add_argument(
    "--verbose", action="store_const",
    dest="loglevel", const=log.INFO, default=log.WARNING,
    help="prints additional info statements",
)
parser.add_argument(
    "-e", "--ext", type=str, nargs='+',
    help="Looks for the following extensions in PATHVAR.\n"
    "Default is [.yaml, .yml]",
)
parser.add_argument(
    "-k", "--keys", metavar="KEY", type=str, nargs='+',
    help="Key nodes where position info will be attached.",
)
parser.add_argument(
    "-o", "--out", metavar="FILE",
    help="""Output file. If not set, prints JSON contents to stdout.""",
    type=argparse.FileType('w'),
    default=sys.stdout,
)
parser.add_argument(
    "--pathvar", type=str, nargs='+',
    help="Input search paths ordered by priority from low to high,\n"
    "in addition to the current folder."
)
parser.add_argument(
    "-s", "--spec", metavar="SPEC",
    help="Options to load from in 'zoticonf.toml' under [zoti-yaml.SPEC]",
)
parser.add_argument(
    "-t", "--tool", type=str,
    help="Name of the tool that will use this output. For logging purpose only.",
)
parser.add_argument(
    "main", nargs="?",
    help="""Qualified name of the main module. Ignored if module is\n"""
    """read from stdin.""",
)
default_args = {
    "ext": [".yaml", ".yml"],
    "keys": [],
    "main": None,
}

args = parser.parse_args()
try:
    log.basicConfig(level=args.loglevel,
                    format='%(levelname)s: %(message)s', stream=sys.stderr)
    conf = _mu.load_config(f"zoti.yaml.{args.spec}" if args.spec else "zoti.yaml",
                           args, default_args)

    # checking configuration
    log.info(f"{conf}")

    # loading inputs
    proj = Project(**conf)
    try:
        pream, text = _mu.read_yaml_from_stdin()
        if not all([x in pream for x in [ATTR_MODULE, ATTR_PATH]]):
            missing = ", ".join([x for x in [ATTR_MODULE, ATTR_PATH]
                                 if x not in pream])
            msg = f"Document at <stdin> is missing preamble entries: {missing}"
            raise IOError(msg)
        conf["main"] = pream[ATTR_MODULE]
        proj.load_module(conf["main"], text, pream[ATTR_PATH], with_deps=True)
    except Exception:
        if not conf["main"]:
            raise ValueError("No main module specified nor piped.")
        log.info("*** Reading sources from files ***")
        path = proj.resolve_path(conf["main"])
        with open(path) as f:
            proj.load_module(conf["main"], f, path, with_deps=True)

    # Building projects
    log.info("*** Building module ***")
    proj.build(conf["main"])
    module = proj.modules[conf["main"]].to_dump()

    # Dumping project
    o_ext = Path(
        args.out.name).suffix if not "stdout" in args.out.name else ".json"
    log.info("*** Dumping module ***")
    if o_ext in [".p", ".pickle"]:
        pickle.dump(module, args.out)
        log.info(f"  - Dumped pickle at {args.out.name}")
    elif o_ext in [".yaml", ".yml"]:
        yaml.dump_all(module, args.out, Dumper=ZotiDumper, default_flow_style=None,
                      explicit_start=True, width=4096,)
        log.info(f"  - Dumped YAML at {args.out.name}")
    elif o_ext == ".json":
        json.dump(module, args.out, indent=2, cls=ZotiEncoder)
        log.info(f"  - Dumped JSON at {args.out.name}")
    else:
        raise ValueError(f"Cannot recognize output format {o_ext}")
except Exception as e:
    Path(args.out.name).unlink(missing_ok=True)
    raise e
