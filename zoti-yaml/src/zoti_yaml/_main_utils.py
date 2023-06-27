import logging as log
import os
import sys
from pathlib import Path
from argparse import Action

import toml
import yaml
import json


def load_config(key, args, default_args):
    keys = key.split(".")
    load_conf = {}
    conf_path = os.getenv("ZOTI_CONF", default="zoticonf.toml")
    conf = {**vars(args), **default_args}
    try:
        with open(conf_path) as f:
            load_conf = toml.load(f)
        for key in keys:
            if key in load_conf:
                load_conf = load_conf[key]
                conf.update({k: load_conf[k] for k in load_conf if k in conf})
            else:
                log.warning(f"Did not find configuration for '{key}' in {conf_path}")
                log.warning("Proceeding with the CLI options!")
                break
    except Exception as e:
        log.warning(f"Could not read configuration file at {conf_path} because:\n{e}")
        log.warning("Proceeding with the default options!")
    conf.update({k: v for k, v in vars(args).items() if bool(v)})
    return conf


def value_error(what, *args):
    msg = ", ".join([f"{k}={v}" for k, v in args])
    raise ValueError(f"{what}: {msg}")


def writer(filepath,  content, mode="w", dumper=lambda f, x: f.write(x)):
    if filepath is None:
        dumper(sys.stdout, content)
    else:
        fpath = Path(filepath)
        fpath.parent.mkdir(parents=True, exist_ok=True)
        with open(fpath, mode) as f:
            dumper(f, content)
        log.info(f"  * Created file {fpath}")


def load_preamble(stream):
    loader = yaml.Loader(stream)
    try:
        assert loader.check_data()
        return loader.get_data()
    except yaml.MarkedYAMLError as e:
        raise e
    finally:
        loader.dispose()


def read_yaml_from_stdin():
    assert not sys.stdin.isatty()
    log.info("*** Reading YAML source from stdin pipe ***")
    text = sys.stdin.read()
    pream = load_preamble(text)
    return (pream, text)


def read_json_from_stdin():
    assert not sys.stdin.isatty()
    log.info("*** Reading JSON source from stdin pipe ***")
    return tuple(json.load(sys.stdin))
