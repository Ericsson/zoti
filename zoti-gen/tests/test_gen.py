import os
import sys
import yaml
from pprint import pprint
from pathlib import PurePosixPath

sys.path.insert(0, "src")
sys.path.insert(0, "tests/inputs")

from zoti_gen.handler import ProjHandler
from zoti_yaml import Module

from pprint import pprint


def test_scenario1() -> None:
    mods = []
    with open("tests/inputs/genspec_main.yaml") as f:
        mods.append(Module(*yaml.load_all(f, Loader=yaml.Loader)))
    with open("tests/inputs/genspec_leafs.yaml") as f:
        mods.append(Module(*yaml.load_all(f, Loader=yaml.Loader)))

    gen = ProjHandler("genspec_leafs", mods)
    gen.parse()
    gen.resolve()

    assert len(gen.decls) == 1
    assert gen.get(**gen.decls[0]).code == "main(in1, in2, acc, &out) {\n out = acc + in1 * in2; \n};"

    gen2 = ProjHandler("main", mods)
    gen2.parse()
    gen2.resolve()
    assert len(gen2.requs.dep_list("include")) == 2
    for cp in gen2.decls:
        assert gen2.get(**cp).code

    try:
        gen2.dump_yaml("tmp.yaml")
        gen2.dump_graph("tmp.dot")
    except Exception as e:
        raise e
    finally:
        os.remove("tmp.dot")
        os.remove("tmp.yaml")
