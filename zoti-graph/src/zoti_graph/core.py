from enum import Flag
from pathlib import PurePosixPath
from typing import Dict
from copy import deepcopy

from zoti_graph.util import SearchableEnum, default_init, default_repr


# meta attributes (added by the loader)
META_UID = "__uid__"

# keywords (read from the user input)
KEY_NODE = "nodes"
KEY_PORT = "ports"
KEY_EDGE = "edges"
KEY_PRIM = "primitives"

# attributes (read from user input)
ATTR_NAME = "name"
ATTR_KIND = "kind"
ATTR_ENT = "entry"
ATTR_REL = "relation"


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


class Rel(Flag, metaclass=SearchableEnum):
    """ Bitwise flags denoting kinds of edges. """

    TREE = 3  # :  011
    CHILD = 1  # : 001 belongs to tree
    PORT = 2  # :  010 belongs to tree
    GRAPH = 4  # : 100
    NONE = 0  # :  000


class Edge:
    """Container for edge entry."""
    mark: Dict
    _info: Dict


##########
## PORT ##
##########


class Port:
    """Container for port entry."""
    name: str
    mark: Dict
    _info: Dict

    def duplicate(self, **kwargs):
        ret = deepcopy(self)
        for k, v in kwargs.items():
            setattr(ret, k, v)
        return ret


###########
## NODES ##
###########


class Node:
    """Base class for a leaf node"""
    name: str
    parameters: Dict
    mark: Dict
    _info: Dict
    
    def duplicate(self, **kwargs):
        ret = deepcopy(self)
        for k, v in kwargs.items():
            setattr(ret, k, v)
        return ret
