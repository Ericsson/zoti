import json
import argparse


def make_headers(include):
    header = """/*
 * Copyright Ericsson 2023 - MIT License
 *
 * DO NOT EDIT THIS FILE!
 * This file is auto-generated and any edits will be overwritten and lost.
 */"""
    header += "\n\n"
    for i in include:
        header += f"#include {i}\n"
    return header


parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", type=str, required=True)
parser.add_argument("-d", "--deps", type=str, required=True)
args = parser.parse_args()

with open(args.deps) as f:
    includes = json.load(f)["include"]

with open(args.file) as f:
    original = f.read()

with open(args.file, "w") as f:
    f.write(make_headers(includes))
    f.write("\n")
    f.write(original)
