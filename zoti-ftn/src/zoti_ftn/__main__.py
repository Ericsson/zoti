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
    dest="loglevel",
    const=log.INFO,
    default=log.WARNING,
)

parser.add_argument(
    '-o', '--out',
    help="Output file. If not specified writes to stdout.",
    type=argparse.FileType('w'),
    default=sys.stdout,
)

parser.add_argument(
    'input',
    nargs='+',
    help="Input file(s).",
)

args = parser.parse_args()

log.basicConfig(level=args.loglevel,
                format='%(levelname)s: %(message)s', stream=sys.stderr)

ftn_srcs = {}
for fpath in args.input:
    i_ext = Path(fpath).suffix
    if i_ext in [".json"]:
        with open(fpath) as f:
            doc = list(json.load(f, Loader=yaml.Loader))
            ftn_srcs[doc[0]["module"]] = doc[1]["entries"]
    elif i_ext in [".yaml", ".yml"]:
        with open(fpath) as f:
            doc = list(yaml.load_all(f, Loader=yaml.Loader))
            ftn_srcs[doc[0]["module"]] = doc[1]["entries"]
    elif i_ext in [".ftn"]:
        with open(fpath) as f:
            doc = list(lang.load_file(f))[0]
            ftn_srcs[doc[0]["module"]] = doc[1]["entries"]
    else:
        raise ValueError("Cannot recognize extension of {infile}")
    


o_ext = Path(args.out.name).suffix
if o_ext in [".yaml", ".yml"]:    
    yaml.dump(ftn_srcs, args.out, default_flow_style=None)
else:
    json.dump(ftn_srcs, args.out, indent=2)
