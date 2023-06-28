from dataclasses import dataclass
from enum import Flag
from typing import Dict, List, Optional

import zoti_graph.core as ty
from zoti_graph.util import SearchableEnum, default_init, default_repr


class Dir(Flag, metaclass=SearchableEnum):
    """ Bitwise flags denoting port directions. """

    NONE = 0  # : 00 (for init)
    IN = 1  # :   01
    OUT = 2  # :  10
    SIDE = 3  # : 11


class Port(ty.Port):
    """Container for port entry."""
    kind: Dir
    port_type: Dict
    data_type: Dict

    @default_init
    def __init__(self, name, kind, port_type={}, data_type={}, mark={}, _info={}, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass

    def is_event(self):
        return self.kind and self.kind != Dir.SIDE

    def is_side(self):
        return self.kind == Dir.SIDE

    def has_dir_in(self):
        return self.kind & Dir.IN != Dir.NONE

    def has_dir_out(self):
        return self.kind & Dir.OUT != Dir.NONE


class Edge(ty.Edge):
    """Container for edge entry."""
    edge_type: Dict

    @default_init
    def __init__(self, edge_type, mark, _info, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass


class CompositeNode(ty.Node):
    """Container for composite node entry"""

    @default_init
    def __init__(self, name, parameters={}, mark={}, _info={}, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass


class SkeletonNode(ty.Node):
    """Container for a skeleton node entry"""
    type: str

    @default_init
    def __init__(self, name, type, parameters={}, mark={}, _info={}, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass


class PlatformNode(ty.Node):
    """Container for platform node entry"""
    target: Dict

    @default_init
    def __init__(self, name, target, parameters={}, mark={}, _info={}, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass


class ActorNode(ty.Node):
    """Container for actor node entry"""

    @dataclass(eq=False)
    class FSM:
        inputs: List[str]
        expr: Dict[str, Dict]
        preproc: Optional[str] = None
        states: Optional[List[str]] = None
        scenarios: Optional[Dict[str, str]] = None

    detector: Optional[FSM]

    @default_init
    def __init__(self, name, parameters={}, mark={}, detector=None, _info={}, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass


class KernelNode(ty.Node):
    """Container for kernel node entry"""
    extern: str

    @default_init
    def __init__(self, name, extern="", parameters={}, mark={}, _info={}, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass


class BasicNode(ty.Node):
    """Container for primitive node entry"""
    type: str

    @default_init
    def __init__(self, name, type, parameters={}, mark={}, _info={}, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass


BASE_GRAPHVIZ_STYLE = {
    "edges": {
        "all": (lambda edge, src, dst, info_f: {
            "arrowhead": "diamond" if isinstance(src, Port) and src.is_side() else "none",
            "arrowtail": "diamond" if isinstance(dst, Port) and dst.is_side() else "normal",
            "dir": "both",
            "label": info_f(edge) if info_f else ""
        })
    },
    "ports": {
        "all": (lambda port, info_f: {
            "shape": "hexagon" if port.is_side() else "rarrow",
            "label": port.name
            + (f": {info_f(port)}" if info_f is not None else "")
        })
    },
    "leafs": {
        "BasicNode": (lambda node, ports, info_f, pinfo_f: {
            "label": "",
            "shape": "doublecircle",
            "style": "filled",
            "width": 0.3,
            "height": 0.3,
            "fillcolor": "yellow",
        } if node.type == "SYSTEM" else {
            "label": "",
            "shape": "invtriangle",
            "width": 0.4,
            "height": 0.25,
            "style": "filled",
            "fillcolor": "black",
        } if node.type == "DROP" else {
            "label": node.type,
            "shape": "oval",
            "fillcolor": "green"
        }),
        "all": (lambda node, ports, info_f, pinfo_f: {
            "shape": "record",
            "style": "rounded",
            "label": "{"
            + ' | '.join([f"<{idp}> {p.name}: {pinfo_f(p) if info_f is not None else ''}"
                          for idp, p in ports if p.kind == Dir.OUT])
            + "} | {" + node.name
            + (f"({node._info['old-name']})" if node._info.get("old-name") else "")
            + (f": {info_f(node)}" if info_f is not None else "")
            + " | {"
            + ' | '.join([f"<{idp}> {p.name}: {pinfo_f(p) if info_f is not None else ''}"
                          for idp, p in ports if p.kind == Dir.SIDE])
            + "} } | {"
            + ' | '.join([f"<{idp}> {p.name}: {pinfo_f(p) if info_f is not None else ''}"
                          for idp, p in ports if p.kind == Dir.OUT])
            + "}"
        })
    },
    "composites": {
        "PlatformNode": (lambda node, info_f: {
            "label": node.name
            + (f"({node._info['old-name']})" if node._info.get("old-name") else "")
            + (f": {info_f(node)}" if info_f is not None else f": node.target['platform']"),
        }),
        "ActorNode": (lambda node, info_f: {
            "style": "rounded",
            "label": node.name
            + (f"({node._info['old-name']})" if node._info.get("old-name") else "")
            + (f": {info_f(node)}" if info_f is not None else ""),
        }),
        "SkeletonNode": (lambda node, info_f: {
            "style": "bold",
            "label": node.name
            + (f"({node._info['old-name']})" if node._info.get("old-name") else "")
            + f": {node.type}",
        }),
        "all": (lambda node, info_f: {
            "style": "dashed",
            "label": node.name
            + (f"({node._info['old-name']})" if node._info.get("old-name") else "")
            + (f": {info_f(node)}" if info_f is not None else ""),
        }),
    }
}
