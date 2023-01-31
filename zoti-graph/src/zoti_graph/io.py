from enum import Flag
from importlib.metadata import distribution

import pydot
from yaml import Dumper, Loader, dump_all, load_all

import zoti_graph.core as ty
import zoti_graph.tokens as tok
from zoti_graph.appgraph import AppGraph

dist = distribution("zoti_graph")


def dump_node_info(AG, stream):
    """Dumps the entry information for all nodes in the *AG* graph as
    plain text to *stream*.

    """
    for n in AG.ir.nodes:
        line = f"* {n}\n  {AG.ir.nodes[n][tok.KEY_ENTRY]}"
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


def draw_graph(
        AG,
        stream,
        root=None,
        max_depth=0,
        platform_info=None,
        actor_info=None,
        composite_info=None,
        leaf_info=None,
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

    root = ty.Uid(root) if root else AG.root

    def _clusName(uid):
        return repr(uid).replace("/", "_").replace("-", "_")

    def _label(uid, extract, extra=None):
        label = AG.entry(uid).name
        label += f" ({extra})" if extra is not None else ""
        label += f": {extract(AG.entry(uid))}" if extract is not None else ""
        return label

    def _draw_ports(parent, node):
        ports = AG.ports(
            node, select=lambda p: p.dir == ty.Dir.IN or p.dir == ty.Dir.OUT
        )
        ioports = AG.ports(node, select=lambda p: p.dir == ty.Dir.INOUT)

        for port in ports:
            parent.add_node(
                pydot.Node(
                    _clusName(port), label=_label(port, port_info), shape="rarrow"
                )
            )
        for port in ioports:
            parent.add_node(
                pydot.Node(
                    _clusName(port),
                    label=_label(port, port_info),
                    shape="hexagon",
                )
            )

    def _draw_leaf(parent, node):
        entry = AG.entry(node)
        pydot_lbl = _label(node, leaf_info, entry._info.get("old-name"))
        pydot_id = _clusName(node)
        iports = [
            f"<{p.name()}> {_label(p, port_info)}"
            for p in AG.ports(node, select=lambda p: p.dir == ty.Dir.IN)
        ]
        oports = [
            f"<{p.name()}> {_label(p, port_info)}"
            for p in AG.ports(node, select=lambda p: p.dir == ty.Dir.OUT)
        ]
        ioport = [
            f"<{p.name()}> {_label(p, port_info)}"
            for p in AG.ports(node, select=lambda p: p.dir == ty.Dir.INOUT)
        ]
        label = f"{{ {' | '.join(iports)} }}"
        label += f" | {{ {pydot_lbl} | {{ {' | '.join(ioport)} }} }} | "
        label += f"{{ {' | '.join(oports)} }}"
        parent.add_node(
            pydot.Node(pydot_id, shape="record",
                       style="rounded", label=label)
        )

    def _draw_primitive(parent, node, entry):
        pydot_id = _clusName(node)
        if entry.type == ty.PrimitiveTy.SYSTEM:
            style = {
                "label": "",
                "shape": "doublecircle",
                "style": "filled",
                "width": 0.3,
                "height": 0.3,
                "fillcolor": "yellow",
            }
        elif entry.type == ty.PrimitiveTy.NULL:
            style = {
                "label": "",
                "shape": "invtriangle",
                "width": 0.4,
                "height": 0.25,
                "style": "filled",
                "fillcolor": "black",
            }
            parent.add_node(pydot.Node(pydot_id, **style))

    def _draw_edge(src, dst):
        def _is_inout(port_id):
            try:
                return AG.entry(port_id).dir == ty.Dir.INOUT
            except AttributeError:
                return False

        src_parent = AG.parent(src)
        dst_parent = AG.parent(dst)

        if AG.is_leaf(src_parent):
            src_port = _clusName(src_parent) + ":" + src.name()
        else:
            src_port = _clusName(src)
        if AG.is_leaf(dst_parent):
            dst_port = _clusName(dst_parent) + ":" + dst.name()
        else:
            dst_port = _clusName(dst)

        src_arrow = "diamond" if _is_inout(src) else "none"
        dst_arrow = "diamond" if _is_inout(dst) else "normal"
        label = edge_info(AG.entry(src, dst)) if edge_info else ""
        graph.add_edge(
            pydot.Edge(
                src_port,
                dst_port,
                arrowtail=src_arrow,
                arrowhead=dst_arrow,
                dir="both",
                label=label,
            )
        )

    def _recursive_build(parent, node, depth):
        pydot_id = _clusName(node)
        children = AG.children(node)
        entry = AG.ir.nodes[node][tok.KEY_ENTRY]
        if children and depth > 0:
            mark = entry._info.get("old-name")
            if isinstance(entry, ty.ActorNode):
                style = {
                    "label": _label(node, actor_info, mark),
                    "style": "rounded",
                }
            elif isinstance(entry, ty.CompositeNode):
                style = {
                    "style": "dashed",
                    "label": _label(node, composite_info, mark),
                }
            elif isinstance(entry, ty.PlatformNode):
                if platform_info is None:
                    def info(x): return x.target["platform"]
                else:
                    def info(x): return platform_info(x)
                style = {"label": _label(node, info, mark)}

            cluster = pydot.Cluster(pydot_id, **style)
            for child in children:
                _recursive_build(cluster, child, depth - 1)
                parent.add_subgraph(cluster)
                _draw_ports(cluster, node)
        else:
            if isinstance(entry, ty.Primitive):
                _draw_primitive(parent, node, entry)
            else:
                _draw_leaf(parent, node)

    depth = max_depth if max_depth else 9999
    graph = pydot.Dot(graph_type="digraph", fontname="Verdana")
    for child in AG.children(root):
        _recursive_build(graph, child, depth)

    for src, dst in AG.only_graph().edges:
        _draw_edge(src, dst)

    graph.write_dot(stream.name)


class AppGraphDumper(Dumper):
    def repr_tuple(self, obj):
        return self.represent_sequence("!tuple", list(obj))

    def repr_uid(self, obj):
        return self.represent_scalar("!Uid", repr(obj))

    def repr_edge(self, obj):
        return self.represent_mapping("!Edge", vars(obj))

    def repr_port(self, obj):
        return self.represent_mapping("!Port", vars(obj))

    def repr_fsm(self, obj):
        return self.represent_mapping("!FSM", vars(obj))

    def repr_flag(self, obj):
        return self.represent_scalar(f"!{type(obj).__name__}", obj.name)

    def repr_node(self, obj):
        return self.represent_mapping(f"!{type(obj).__name__}", vars(obj))

    def ignore_aliases(self, data):
        return True


AppGraphDumper.add_representer(tuple, AppGraphDumper.repr_tuple)
AppGraphDumper.add_representer(ty.Uid, AppGraphDumper.repr_uid)
AppGraphDumper.add_representer(ty.ActorNode.FSM, AppGraphDumper.repr_fsm)
AppGraphDumper.add_representer(ty.Edge, AppGraphDumper.repr_edge)
AppGraphDumper.add_representer(ty.Port, AppGraphDumper.repr_port)
AppGraphDumper.add_multi_representer(Flag, AppGraphDumper.repr_flag)
AppGraphDumper.add_multi_representer(ty.NodeABC, AppGraphDumper.repr_node)


class AppGraphLoader(Loader):
    def cons_tuple(self, node):
        return tuple(self.construct_sequence(node))

    def cons_uid(self, node):
        return ty.Uid(self.construct_scalar(node))

    def cons_edge(self, node):
        return ty.Edge(**self.construct_mapping(node, deep=True))

    def cons_port(self, node):
        return ty.Port(**self.construct_mapping(node, deep=True))

    def cons_relation(self, node):
        return ty.Relation[self.construct_scalar(node)]

    def cons_dir(self, node):
        return ty.Dir[self.construct_scalar(node)]

    def cons_primtype(self, node):
        return ty.PrimitiveTy[self.construct_scalar(node)]

    def cons_fsm(self, node):
        return ty.ActorNode.FSM(**self.construct_mapping(node, deep=True))

    def cons_compositenode(self, node):
        return ty.CompositeNode(**self.construct_mapping(node, deep=True))

    def cons_primitivenode(self, node):
        return ty.Primitive(**self.construct_mapping(node, deep=True))

    def cons_platformnode(self, node):
        return ty.PlatformNode(**self.construct_mapping(node, deep=True))

    def cons_actornode(self, node):
        return ty.ActorNode(**self.construct_mapping(node, deep=True))

    def cons_kernelnode(self, node):
        return ty.KernelNode(**self.construct_mapping(node, deep=True))


AppGraphLoader.add_constructor("!tuple", AppGraphLoader.cons_tuple)
AppGraphLoader.add_constructor("!Uid", AppGraphLoader.cons_uid)
AppGraphLoader.add_constructor("!Edge", AppGraphLoader.cons_edge)
AppGraphLoader.add_constructor("!Port", AppGraphLoader.cons_port)
AppGraphLoader.add_constructor("!Relation", AppGraphLoader.cons_relation)
AppGraphLoader.add_constructor("!Dir", AppGraphLoader.cons_dir)
AppGraphLoader.add_constructor("!PrimitiveTy", AppGraphLoader.cons_primtype)
AppGraphLoader.add_constructor(
    "!CompositeNode", AppGraphLoader.cons_compositenode)
AppGraphLoader.add_constructor("!Primitive", AppGraphLoader.cons_primitivenode)
AppGraphLoader.add_constructor(
    "!PlatformNode", AppGraphLoader.cons_platformnode)
AppGraphLoader.add_constructor("!ActorNode", AppGraphLoader.cons_actornode)
AppGraphLoader.add_constructor("!FSM", AppGraphLoader.cons_fsm)
AppGraphLoader.add_constructor("!KernelNode", AppGraphLoader.cons_kernelnode)


def dump_raw_yaml(G, stream):
    """Serializes graph *G* to YAML and dumps it to *stream*. The stream
    will contain a 4-tuple:

    - the UID of the root node
    - the version of zoti-graph (to be compared when loading)
    - a list of all node entries in the graph.
    - a list of all edge entries in the graph.
    """
    dump_all([
        repr(G.root),
        dist.version,
        list(G.ir.nodes(data=True)),
        list(G.ir.edges(data=True))
    ], stream, Dumper=AppGraphDumper, default_flow_style=None,)


def from_raw_yaml(stream, version=None) -> AppGraph:
    """Deserializes a graph from a *stream* containing the raw YAML data
    as dumped by :meth:`dump_raw_yaml`. If *version* is passed, it
    will compare it against the loaded version and raise an error if
    they do not match.

    """

    root, ver, nodes, edges = tuple(load_all(stream, Loader=AppGraphLoader))
    G = AppGraph(root)
    if version and version != ver:
        msg = f"Cannot load {stream.name}. Document format version "
        msg += f"{ver} does not match with tool version {version}"
        raise Exception(msg)
    G.ir.add_nodes_from(nodes)
    G.ir.add_edges_from(edges)
    return G
