from zoti_yaml.dumper import ZotiDumper
from zoti_yaml import Project, Module, Pos, PosStack, get_pos
import os
import sys
import yaml
from pprint import pprint
from pathlib import PurePosixPath

sys.path.insert(0, "src")


def test_scenario1() -> None:
    proj = Project(keys=["root", "nodes"],
                   pathvar=["tests/scenario1"],
                   ext=[".zoml"]
                   )
    path = proj.resolve_path("main")
    with open(path) as f:
        proj.load_module("main", f, path)
    # pprint(proj.modules["main"].doc)
    assert len(proj.modules) == 3
    print(proj.modules.keys())
    proj.build("mod1")
    proj.build("main")
    pprint(proj.modules["main"].doc)
    main = proj.modules["main"]
    assert main.get("/root[n1]/mark") == "DEFAULT_MARKING"
    assert main.get("/root[n2]/mark") == "DEFAULT_MARKING"
    assert main.get("/root[n2]/_info/_prev_attrs/name") == "n1"
    assert main.get("/root[0]/_info") is not None
    assert main.get("/root[n1]/nodes[n1_n2]/data") == "Hello World!"
    assert main.get(
        "/root[n1]/nodes[n1_n1]/nodes[n1_n1_n1]/data") == "I am referenced by n1_n1_n1!"
    print(get_pos(main.get("/root[0]")).show())
    # print(main.get("/root[0]/_info/_pos")[0].show())

    dumped = yaml.dump_all(
        [main.preamble, main.doc],
        Dumper=ZotiDumper,
        default_flow_style=None,
        explicit_start=True,
        width=4096,
    )
    try:
        with open("tmp.yaml", "w") as f:
            f.write(dumped)
        with open("tmp.yaml") as f:
            raw = yaml.load_all(f, Loader=yaml.SafeLoader)
            mod = Module(*raw)
            assert mod.name == "main"
            assert isinstance(get_pos(mod.get("root[0]")), PosStack)
            assert isinstance(mod.get("root[0]/_info/_pos[0]"), list)
            assert mod.get("root[n2]/floating-ref/path") == '/root[n1]'
            assert mod.get(
                "root[n2]/passed-arg") == "This field is used only to pass caller argument and will be destroyed"
    except Exception as e:
        raise e
    finally:
        # os.remove("tmp.yaml")
        pass
