import pydot
import yaml
import logging as log
from importlib.metadata import distribution

import zoti_yaml as zoml
import zoti_gen.util as util
from zoti_gen.core import Block, Label, Requirement

dist = distribution("zoti_gen")


class ZotiGenLoader(zoml.LoaderWithInfo):
    """YAML loader class with information for ZOTI-Graph inputs."""

    def __init__(self, stream, **kwargs):
        super(ZotiGenLoader, self).__init__(stream)
        self._tool = dist.name + "-" + dist.version
        self._key_nodes = ["block", "label", "instance", "bind"]


def print_zoti_yaml_keys():
    return ["block", "label", "instance", "bind"]


def dump_yaml(B, path):
    """Dumps all parsed blocks up to this point as a YAML file."""
    with open(path, "w") as f:
        doc = {k: Block.Schema().dump(v) for k, v in B._blks.items()}
        f.write(yaml.dump(doc,
                          Dumper=yaml.Dumper,
                          default_flow_style=None))
        log.info(f"  * Dumped yaml spec at '{f.name}'")


def dump_graph(B, dot_file, rankdir="LR") -> None:
    """Dumps a DOT graph representation of the current block structure
    starting from the top block inwards."""
    def _recursive(parent, name, comp, fill=False):
        style = {
            "style": "filled",
            "shape": "record",
            "label": f"{comp.name} : {util.qualname(comp)}",
        }
        if fill:
            style["fillcolor"] = "lightgrey"
        else:
            style["fillcolor"] = "white"
            style["color"] = "black"

        p = pydot.Cluster(name, **style)

        # assumes labels/params are still lists
        for key, label in comp.label.items():
            style = {"label": label.name, "shape": "oval"}
            p.add_node(pydot.Node(f"{name}-{key}", **style))
        for key in comp.param.keys():
            style = {"label": key, "shape": "parallelogram"}
            p.add_node(pydot.Node(f"{name}-{key}", **style))

        for inst in comp.instance:
            ccomp = B.get(inst.block)
            cname = f"{name}.{ccomp.name}"
            _recursive(p, cname, ccomp, not fill)
            for bind in inst.bind:
                bname = f"{cname}-{bind.args['child']}"
                if bind.func == "value_to_param":
                    p.add_node(pydot.Node(
                        bind.args["value"], shape="plain"))
                    p.add_edge(pydot.Edge(bind.args["value"], bname))
                elif bind.func == "usage_to_label":
                    p.add_node(pydot.Node(
                        bind.args["usage"].string, shape="plain"))
                    p.add_edge(pydot.Edge(
                        bind.args["usage"].string, bname))
                else:
                    pname = f"{name}-{bind.args['parent']}"
                    p.add_edge(pydot.Edge(bname, pname))
        parent.add_subgraph(p)

    dot = pydot.Dot(graph_type="digraph",
                    fontname="Verdana", rankdir=rankdir)
    top = B.get(B.main)
    _recursive(dot, repr(B.main), top)
    dot.write_dot(dot_file)
    log.info(f"  * Dumped codeblocks graph at '{dot_file}'")
