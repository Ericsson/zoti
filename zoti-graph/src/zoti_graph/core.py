from dataclasses import dataclass
from enum import Flag
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional

from zoti_graph.util import SearchableEnum, default_init, default_repr


class Uid:
    """Class denoting unique identifiers for hierarchically organized
    entities. Internally is based on ``PurePosixPath`` from `pathlib
    <https://docs.python.org/3/library/pathlib.html>`_.

    :param uid: if ``None`` then the root path ``/`` is assumed

    """

    _uid: PurePosixPath

    def __init__(self, uid=None):
        if isinstance(uid, PurePosixPath):
            self._uid = uid
        elif uid:
            self._uid = PurePosixPath(uid)
        else:
            self._uid = PurePosixPath("/")

    def __repr__(self):
        return self._uid.as_posix()

    def __eq__(self, other):
        if other:
            return self._uid == other._uid
        else:
            return False

    def __lt__(self, other):
        return len(self._uid.parts) < len(other._uid.parts)

    def __gt__(self, other):
        return len(self._uid.parts) > len(other._uid.parts)

    def __hash__(self):
        return hash(self._uid)

    def name(self):
        """ Returns the (base)name from a path. """
        basename = self._uid.name
        return basename[1:] if basename.startswith("^") else basename

    def parent(self):
        """ Returns the ID of the parent of this entity. """
        return Uid(self._uid.parent)

    def withNode(self, name: str):
        """ Builds a child node ID by appending its name to this path. """
        return Uid(self._uid.joinpath(name))

    def withPort(self, name: str):
        """ Builds a port ID by appending its name to this path. """
        return Uid(self._uid.joinpath("^" + name))

    def withPath(self, path, port=None):
        """Builds an ID by appending a given path to this one. if the ``port``
        argument is also provided, it creates a port ID.

        """
        if port is not None:
            newpath = self._uid.joinpath(path._uid).joinpath("^" + port)
        else:
            newpath = self._uid.joinpath(path._uid)
        return Uid(newpath)

    def withSuffix(self, suffix):
        """ adds only a suffix string to the current id. """
        return Uid(self._uid.with_name(f"{self._uid.name}_{suffix}"))

    def replaceRoot(self, old_root, new_root):
        while not self._uid.is_relative_to(old_root._uid) and old_root:
            old_root = old_root.parent()
        path = self._uid.relative_to(old_root._uid)
        return Uid(new_root._uid.joinpath(path))


##########
## EDGE ##
##########


class Relation(Flag, metaclass=SearchableEnum):
    """ Bitwise flags denoting kinds of edges. """

    ONLY_TREE = 3  # :   0011
    CHILD = 1  # :       0001 belongs to tree
    PORT = 2  # :        0010 belongs to tree
    ONLY_GRAPH = 12  # : 1100
    EVENT = 4  # :       0100 belongs to graph
    STORAGE = 8  # :     1000 belongs to graph
    NONE = 0  # :        0000


class Edge:
    """Container for edge entry."""
    edge_type: Dict
    kind: Relation
    mark: Dict
    _info: Dict

    @default_init
    def __init__(self, edge_type, kind, mark, _info, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass


##########
## PORT ##
##########


class Dir(Flag, metaclass=SearchableEnum):
    """ Bitwise flags denoting port directions. """

    NONE = 0  # :  00 (for init)
    IN = 1  # :    01
    OUT = 2  # :   10
    INOUT = 3  # : 11


class Port:
    """Container for port entry."""
    name: str
    dir: Dir
    port_type: Dict
    data_type: Dict
    mark: Dict
    _info: Dict

    @default_init
    def __init__(self, name, dir, port_type={}, data_type={}, mark={}, _info={}, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass

    def is_in(self):
        return self.dir & Dir.IN != Dir.NONE

    def is_out(self):
        return self.dir & Dir.OUT != Dir.NONE


class PrimitiveTy(Flag, metaclass=SearchableEnum):
    """ Bitwise flags denoting types of primitives. """

    NULL = 0
    SYSTEM = 1
    BYPASS = 2


class Primitive():
    """Container for primitive node entry"""
    name: str
    type: PrimitiveTy
    mark: Dict
    _info: Dict

    @default_init
    def __init__(self, name, type, mark={}, _info={}, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass

    def is_type(self, type):
        if isinstance(type, PrimitiveTy):
            return self.type == type
        if isinstance(type, str):
            return self.type == PrimitiveTy[type]
        raise TypeError(type)


###########
## NODES ##
###########


class NodeABC:
    """Base class for a node"""
    name: str
    parameters: Dict
    mark: Dict
    _info: Dict


class CompositeNode(NodeABC):
    """Container for composite node entry"""

    @default_init
    def __init__(self, name, parameters={}, mark={}, _info={}, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass


class PlatformNode(NodeABC):
    """Container for platform node entry"""
    target: Dict

    @default_init
    def __init__(self, name, target, parameters={}, mark={}, _info={}, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass


class ActorNode(NodeABC):
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


class KernelNode(NodeABC):
    """Container for kernel node entry"""
    extern: str

    @default_init
    def __init__(self, name, extern="", parameters={}, mark={}, _info={}, **kwargs):
        pass

    @default_repr
    def __repr__(self):
        pass
