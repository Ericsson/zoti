from enum import Flag
from importlib.metadata import distribution

import pydot
import pickle

import zoti_yaml as zoml
import zoti_graph.core as ty
import zoti_graph.genny.core as genny_core
import zoti_graph.genny.parser as genny_parse
from zoti_graph.appgraph import AppGraph

DIST = distribution("zoti_graph")
GRAPHVIZ_STYLE = {
    "genny": genny_core.BASE_GRAPHVIZ_STYLE
}
NODE_FIELD = {
    "genny": genny_parse.NodeChoiceField()
}
EDGE_SCHEMA = {
    "genny": genny_parse.EdgeParser()
}


class ZotiGraphLoader(zoml.LoaderWithInfo):
    """YAML loader class with information for ZOTI-Graph inputs."""

    def __init__(self, stream, **kwargs):
        super(ZotiGraphLoader, self).__init__(stream)
        self._tool = DIST.name + "-" + DIST.version
        self._key_nodes = ["nodes", "ports", "edges"]


def print_zoti_yaml_keys():
    return ["nodes", "ports", "edges"]


def dump_node_info(AG, stream):
    """Dumps the entry information for all nodes in the *AG* graph as
    plain text to *stream*.

    """
    for n in AG.ir.nodes:
        line = f"* {n}\n  {AG.ir.nodes[n][ty.KEY_ENTRY]}"
        stream.write(line + "\n")


def draw_tree(AG, stream, root=None, with_ports=True, **kwargs):
    """Draws only the hierarchical structure of the *AG* graph in a DOT
    file dumped to *stream*.

    To draw only the sub-graph under an arbitrary node its UID should
    be passed as the *root* argument.

    *with_ports* toggles whether ports should be present in the plot
     or not.

    """
    graph = pydot.Dot(graph_type="digraph", fontname="Verdana")
    for src, dst in AG.only_tree(root, with_ports).edges:
        graph.add_edge(pydot.Edge(str(src), str(dst)))
        graph.set_rankdir("LR")
        graph.write_dot(stream.name)


def draw_graphviz(
        AG,
        stream,
        root=None,
        max_depth=0,
        node_info=None,
        port_info=None,
        edge_info=None,
        **kwargs
):
    """Draws the *AG* graph, starting with *root* as top component and
    dumps the drawing in a DOT file in *stream*. If *max_depth* is not
    a positive number it is considered "infinite".

    The rest of the arguments are extraction functions for printing
    additional info (see `Core types`_).

    """

    assert GRAPHVIZ_STYLE[AG._instance]  # No Graphviz style for format
    root = ty.Uid(root) if root else AG.root

    def _make_style(key, entry, *args):
        try:
            style = GRAPHVIZ_STYLE[AG._instance][key]
        except KeyError:
            raise KeyError(
                f"Format '{AG._instance}' does not have a Graphviz style for {key}")
        if type(entry).__name__ in style:
            return style[type(entry).__name__](entry, *args)
        else:
            return style["all"](entry, *args)

    def _dot_id(uid):
        return repr(uid).replace("/", "_").replace("-", "_")

    def _draw_edge(src, dst):
        src_parent = AG.parent(src)
        dst_parent = AG.parent(dst)

        if AG.is_leaf(src_parent):
            src_port = _dot_id(src_parent) + ":" + src.name()
        else:
            src_port = _dot_id(src)
        if AG.is_leaf(dst_parent):
            dst_port = _dot_id(dst_parent) + ":" + dst.name()
        else:
            dst_port = _dot_id(dst)

        dot_edge = pydot.Edge(
            src_port,
            dst_port,
            **_make_style("edges", AG.edge(src, dst),
                          AG.entry(src), AG.entry(dst), edge_info)
        )
        graph.add_edge(dot_edge)

    def _recursive_build(parent, node, depth):
        children = AG.children(node)
        if children and depth > 0:
            cluster = pydot.Cluster(
                _dot_id(node),
                **_make_style("composites", AG.entry(node), node_info))
            for child in children:
                _recursive_build(cluster, child, depth - 1)
            for port in AG.ports(node):
                dot_port = pydot.Node(
                    _dot_id(port),
                    **_make_style("ports", AG.entry(port), port_info)
                )
                cluster.add_node(dot_port)
            parent.add_subgraph(cluster)
        else:
            dot_node = pydot.Node(
                _dot_id(node),
                **_make_style("leafs", AG.entry(node),
                              [(p, AG.entry(p)) for p in AG.ports(node)],
                              node_info, port_info)
            )
            parent.add_node(dot_node)

    depth = max_depth if max_depth else 9999
    graph = pydot.Dot(graph_type="digraph", fontname="Verdana")
    for child in AG.children(root):
        _recursive_build(graph, child, depth)

    for src, dst in AG.only_graph().edges:
        _draw_edge(src, dst)

    graph.write_dot(stream.name)


def dump_raw(G):
    """Serializes graph *G* to raw pickle and dumps it to *stream*. The
    stream will contain a 4-tuple:

    - the version of zoti-graph (to be compared when loading)
    - the name of the current graph format
    - the UID of the root node
    - a list of all node entries in the graph.
    - a list of all edge entries in the graph.

    """
    assert NODE_FIELD[G._instance]
    assert EDGE_SCHEMA[G._instance]

    return [
        DIST.version,
        G._instance,
        repr(G.root),
        [(repr(uid), NODE_FIELD[G._instance]._serialize(G.entry(uid), "node", {}))
         for uid in G.ir.nodes],
        [(repr(src), repr(dst), data[ty.ATTR_REL].name,
          EDGE_SCHEMA[G._instance].dump(data[ty.ATTR_ENT]) if ty.ATTR_ENT in data else {})
         for src, dst, data in G.ir.edges(data=True)]
    ]


def from_raw(doc, version=None) -> AppGraph:
    """Deserializes a graph from a *stream* containing the raw pickled
    data as dumped by :meth:`dump_raw`. If *version* is passed, it
    will compare it against the loaded version and raise an error if
    they do not match.

    """

    ver, inst, root, nodes, edges = tuple(doc)
    G = AppGraph(inst, root)
    if version and version != ver:
        msg = f"Cannot load document. Document format version "
        msg += f"{ver} does not match with tool version {version}"
        raise Exception(msg)
    for uid, entry in nodes:
        G.ir.add_node(ty.Uid(uid), **{ty.ATTR_ENT: entry})
    for src, dst, rel, entry in edges:
        G.ir.add_edge(ty.Uid(src), ty.Uid(dst),
                      **{ty.ATTR_REL: ty.Rel[rel], ty.ATTR_ENT: entry})
    return G
