import logging as log
from copy import deepcopy
from pathlib import Path, PurePosixPath
from pprint import pformat
from typing import Any, Dict, List, Optional, Union, Generic, TypeVar
from dataclasses import dataclass

import yaml

INFO = "_info"
POS = "_pos"
RESERVED_KWS = [INFO, POS]

ATTR_NAME = "name"
ATTR_PATH = "path"
ATTR_MODULE = "module"
ATTR_IMPORT = "import"
ATTR_ALIAS = "as"


def clean(node):
    if isinstance(node, list):
        return [clean(n) for n in node]
    if isinstance(node, dict):
        return {
            k: clean(v)
            for k, v in node.items()
            if k not in RESERVED_KWS
        }
    return node


###############
## Positions ##
###############


class Pos:
    """Container for positional information in a YAML file. Depends on
    the info from a PyYAML loader."""

    line: int
    """line number"""

    column: int
    """column number"""

    ibegin: int
    """start index in the text file"""

    iend: int
    """end index in the text file"""

    path: str
    """location of the source file"""

    who: Optional[str]
    """string for bookkeeping the processing pipeline for this node"""

    def __init__(self, line, column, ibegin=0, iend=-1, path="<stdio>", who=None):
        self.line = line
        self.column = column
        self.ibegin = ibegin
        self.iend = iend
        self.path = path
        self.who = who

    @classmethod
    def from_mark(cls, start_mark: yaml.Mark, end_mark: yaml.Mark,
                  path: str = "<stdio>", who: Optional[str] = None):
        return cls(
            start_mark.line,
            start_mark.column,
            start_mark.index,
            end_mark.index,
            path,
            who,
        )

    def __repr__(self):
        rep = f'in "{self.path}", '
        rep += f"line {self.line+1}, column {self.column+1}"
        return rep

    def dump(self) -> List:
        """Dump content to a JSON list of arguments that can be used to
        recreate it.
        """
        return [self.line, self.column, self.ibegin, self.iend, self.path, self.who]

    def show(self) -> str:
        """Pretty print content. Checks `logging.root.level`."""
        rep = repr(self)
        if log.root.level > log.WARN:  # silent
            return rep
        if Path(self.path).is_file():
            with open(self.path) as f:
                if log.root.level < log.WARN:  # verbose
                    rep += f" {self.who}:\n"
                    rep += f.read()[self.ibegin: self.iend]
                else:
                    rep += f" {self.who}:\n  "
                    rep += list(f.readlines())[self.line][:-1]
                    rep += f'\n  {" " * self.column}^'
        return rep


class PosStack:
    """A stack containing the history of attached positional informations."""
    _stack: List[Pos]

    def __init__(self, stack):
        self._stack = stack

    def __repr__(self):
        return repr(self._stack[0])

    def show(self):
        ret = list(reversed(self._stack))
        print(ret)
        return "".join([f"\n  {repr(p)}" for p in ret[:-1]]) + f"\n  {ret[-1].show()}"


def attach_pos(node: Dict, pos: Pos, to_head=False) -> None:
    """Helper function to attach position information to an JSON object"""
    if isinstance(node, dict):
        if INFO in node and POS in node[INFO] and node[INFO][POS] and to_head:
            node[INFO][POS].insert(0, pos.dump())
        elif INFO in node and POS in node[INFO] and node[INFO][POS]:
            node[INFO][POS].append(pos.dump())
        elif INFO in node:
            node[INFO][POS] = [pos.dump()]
        else:
            node[INFO] = {POS: [pos.dump()]}
    elif hasattr(node, INFO):
        tmp = {INFO: getattr(node, INFO)}
        attach_pos(tmp)
        setattr(node, INFO, tmp[INFO])
    else:
        log.debug(f"Could not attach position to object: {repr(node)}")


# def get_pos(node: Dict) -> Optional[Pos]:
#     """Helper function to retrieve position information from a node, if any."""
#     try:
#         if isinstance(node, dict):
#             return Pos(*node[INFO][POS][0])
#         else:
#             return Pos(*getattr(node, INFO)[POS][0])
#     except Exception:
#         return None
def get_pos(node: Dict) -> Optional[PosStack]:
    """Helper function to retrieve position information from a JSON node, if any."""
    try:
        if isinstance(node, dict):
            return PosStack([Pos(*p) for p in node[INFO][POS]])
        else:
            return PosStack([Pos(*p) for p in getattr(node, INFO)[POS]])
    except Exception:
        return None


def get_all_pos(node: Dict) -> Optional[List[Pos]]:
    try:
        if isinstance(node, dict):
            return [Pos(*p) for p in node[INFO][POS]]
        else:
            return [Pos(*p) for p in getattr(node, INFO)[POS]]
    except Exception:
        return None


##########
## !ref ##
##########


T = TypeVar('T')


class Ref(Generic[T]):
    """Reference to an element in a module. When resolved, this object
    contains the qualified name or path to a (unique) element. It may
    have the following keyword arguments:

    *module*: (optional, string)
      A module name or an alias. It resolves to an explicit name. If
      none is specified it is assumed to be the current module.

    *path*: (mutually exlusive with *name*, string)
      A path to an element in the tree (see :class:`TreePath`).

    *name*: (mutually exlusive with *path*, string)
      An identifier of the element in a certain module.

    The type of the reference depends on which tool in the downstream
    uses it. If the tool works with, e.g. JSON trees (similar to
    ZOTI-YAML) then specifying *path* is more reasonable as it is
    being constructed into a :class:`TreePath` handler. However, if
    the tool works with other type of element identifiers, *name*
    should be used, as it preserves the string for downstream
    manipulation.

    Example:

    .. code-block:: yaml

         module: Foo
         import: {module: Foo.Bar, as: Baz}
         ---
         root:
           - ref1: !ref {path: ../../ref2}
           - ref2: !ref {module: Baz, name: "egg"}

    resolves to:

    .. code-block:: yaml

         module: Foo
         import: {module: Foo.Bar, as: Baz}
         ---
         root:
           - ref1: {module: Foo, path: ../../ref2}
           - ref2: {module: Foo.Bar, name: "egg"}
    """

    module: Optional[str]
    path: T

    def __init__(self, module=None, path=None, name=None):
        if not (bool(path) != bool(name)):
            msg = "Either 'path' or 'name' needs to be provided, but not both."
            raise TypeError(msg)
        self.module = module
        if name:
            self.path = name
        if path:
            self.path = TreePath(path)

    def __repr__(self):
        return f"{self.module if self.module else ''}.{self.path}"

    def resolve(self, this=None, root=None):
        if self.module is None:
            self.module = this
        if root is not None and isinstance(self.path, TreePath):
            self.path.resolve(root)
        log.info("  - reference resolved: %s", str(self))


class TreePath:
    """Simple structure used to reference subtrees/nodes using a
    sytax similar to::

        {/path/to/node}

    The ``{path/to/node}`` part is stored as a PurePosixPath, thus it
    can also be a relative path.

    OBS: dot separator between the module part and the path part is
    mandatory even if no module is specified (i.e. current module).

    """

    path: PurePosixPath

    def __init__(
            self, path: Union[str, PurePosixPath] = ""):
        if not isinstance(path, PurePosixPath):
            path = PurePosixPath(path)
        self.path = path
        self.is_resolved = False

    def __repr__(self):
        return self.path.as_posix()

    def is_relative(self):
        return self.path.root == ""

    def relative_to(self, root: "TreePath") -> "TreePath":
        glob = list(root.path.joinpath(self.path).parts)
        done = False
        while not done:
            for idx, part in enumerate(glob):
                if part == "..":
                    assert idx > 0
                    del glob[idx - 1: idx + 1]
                    break
                if idx == len(glob) - 1:
                    done = True
        return TreePath(PurePosixPath(*glob))

    def resolve(self, root) -> None:
        if self.is_resolved:
            return
        if root is not None and self.is_relative():
            ref = self.relative_to(root)
            self.path = ref.path
        self.is_resolved = True

    def with_key(self, key):
        return TreePath(self.path.joinpath(key))

    def with_name(self, name):
        name = name if isinstance(name, str) else str(name)
        parent = self.path.name
        return TreePath(self.path.with_name(f"{parent}[{name}]"))


#############
## !attach ##
#############

class Attach:
    """Attaches a referenced node at the current location. This command
    can have any number of keyword arguments, of which one needs to be
    *ref*.

    *ref*: (object)
      Qualified :class:`TreePath` reference. The *path* is absolute
      (i.e. relative to the root of the *module*) if it starts with a
      ``/`` or relative to this node otherwise.

    *...*: (keyword pairs)
      Arbitrary entries passed to the attached node in the following
      conditions:

        - if the attached node is not an object (i.e. dictionary),
          these entries are ignored;

        - if the attached node is an object but does not contain the
          said entry, it is ignored;

        - if the attached node is an object and contains the said
          entry, the argument entry replaces the original one. The
          original entry is stored at path ``_info/_prev_attrs``
          underneath the attached node.

    *OBS*: If both the parent and referenced nodes contain positional
    information, this will be captured in the ``_info/_pos`` entry,
    whose head will point to the original position of the referenced
    node.

    *OBS2*: ``!ref`` commands are resolved before ``!attach``, thus
    they can be used to construct references.


    Example:

    .. code-block:: yaml

         module: Foo
         ---
         root:
           !attach
           ref: {module: Bar, path: /root[bar]/refd}
           a: this replaces the original
           b: this is ignored

    .. code-block:: yaml

         module: Bar
         ---
         root:
           - name: bar
             refd:
               a: this is replaced
               c: this is carried from the original


    resolves to:

    .. code-block:: yaml

         module: Foo
         ---
         root:
           a: this replaces the original
           c: this is carried from the original

    Module ``Bar`` remains unchanged.

    """

    def __init__(self, ref, pos, _info=None, concat=[], **kwargs):
        if not isinstance(ref, Ref):
            raise ValueError("value given is not of 'ref' type")
        self.ref = ref
        self.pos = pos
        self.concat = concat
        self.pos.who = f"{pos.who}:!attach"
        self.extra = kwargs

    def __repr__(self):
        return "!attach " + repr({"ref": self.ref, **self.extra})

    def resolve(self, modules):
        """OBS: Does not add new entries to the attached node!"""
        if self.ref.module not in modules:
            raise KeyError(f"Module '{self.ref.module}' not loaded.")
        refnode = deepcopy(modules[self.ref.module].get(
            self.ref.path, strict=False))
        if isinstance(refnode, list):
            log.info("  - attached node: %s", repr(self.ref))
            return refnode + self.concat
        if not isinstance(refnode, dict):
            log.info("  - attached node: %s", repr(self.ref))
            return refnode

        # update metadata of the retreived node
        attach_pos(refnode, self.pos)
        refnode[INFO]["_prev_attrs"] = {}
        # _merge_dict(refnode, node, replace=True)

        # update values to the one specified in the "!attach" entry
        # store previous values just in case
        for k, v in {k: v for k, v in refnode.items()
                     if k in self.extra and k != INFO}.items():
            refnode[k] = self.extra[k]
            refnode[INFO]["_prev_attrs"][k] = v

        # replace node altogether
        log.info("  - attached node: %s", repr(self.ref))
        return refnode


##############
## !default ##
##############

@dataclass(eq=False)
class WithCreate:
    """See ``!default``."""

    obj: Any


@dataclass(eq=False)
class WithReplace:
    """See ``!default``."""
    obj: Any


class Default:
    """This keyword is followed by a list of exactly 2 YAML objects (e.g.,
    trees), *defaults* and *original*. When the document tree is being
    resolved, it recursivvely fills in the contents of *original*
    according to the values in *defaults* as per the following rules:

    - both *original* and *defaults* need to be of the same
      (recursive) type;

    - whenever a list is being parsed only the first element of
      *defaults* is being considered for defaulting every element of
      *original*;

    - if an object key is found both in *original* and *defaults*:

      - if the *defaults* entry is a normal object it proceeds with
        the recursive resolving as usual.

      - if the *defaults* entry is preceded by a ``!with_replace``
        keyword it completely overwrites the *original* entry.

    - if an object key is found in *defaults* but not in *original*:

      - if the *defaults* entry is a normal object it ignores it.

      - if the *defaults* entry is preceded by a ``!with_create``
        keyword it creates the new keyword in *original* and
        associates its entry.

    Example:

    .. code-block:: yaml

         !default
         - root:
           - foo:
               a: this is superseded by original
               b: !with_replace this supersedes the original
               c: this will be ignored
               d: !with_create this is created
           - bar: this is ignored (only the first element in a list matters)
         - root:
           - foo:
               a: this supersedes the default value
               b: this is superseded by the default value
           - foo:
               d: this supersedes the default value

    resolves to:

    .. code-block:: yaml

         root:
           - foo:
               a: this supersedes the default value
               b: this supersedes the original
               d: this is created
           - foo:
               b: this supersedes the original
               d: this supersedes the default value

    """

    def __init__(self, defaults, original):
        if type(defaults) != type(original):
            raise ValueError("Aguments of !default of different type.")
        self.defaults = defaults
        self.original = original

    def __repr__(self):
        return "!default\n" + pformat([self.defaults, self.original])

    def resolve(self):
        def _merge_dict(orig: Dict, default: Dict) -> Any:
            def _merge_val(key, val):
                if isinstance(val, WithReplace):
                    orig[key] = deepcopy(val.obj)
                    return
                elif isinstance(val, WithCreate):
                    val = val.obj
                    if key not in orig:
                        orig[key] = deepcopy(val)
                        return
                if key in orig:
                    orig[key] = _merge_dict(orig[key], val)
                return

            if type(orig) != type(default):
                print(default, orig)
                msg = f"Cannot merge {type(default).__name__} with {type(orig).__name__}"
                msg += f"\n  {pformat(default)}"
                msg += f"\n  {pformat(orig)}"
                raise ValueError(msg)
            if isinstance(orig, dict):
                for key, val in default.items():
                    _merge_val(key, val)
            elif isinstance(orig, list):
                # if len(default) != 1:
                #     err = f"Length of default list should be 1.\n{pformat(default)}"
                #     raise ValueError(err)
                orig = [_merge_dict(element, default[0]) for element in orig]
            elif not orig:
                orig = deepcopy(default)
            return orig

        _merge_dict(self.original, clean(self.defaults))
        log.info("  - default values applied")
        return self.original
