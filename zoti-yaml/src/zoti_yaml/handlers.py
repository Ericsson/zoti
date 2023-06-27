import logging as log
from datetime import datetime
from pathlib import Path, PurePosixPath
from pprint import pformat
from typing import Dict, List, Union

import marshmallow as mm

import zoti_yaml.core as ty
from zoti_yaml.exceptions import MarkedError, SearchError
from zoti_yaml.loader import ZomlLoader, load


class PreambleSchema(mm.Schema):
    class Meta:
        unknown = mm.INCLUDE

    name = mm.fields.String(required=True, data_key=ty.ATTR_MODULE)
    impt = mm.fields.List(mm.fields.Nested(
        mm.Schema.from_dict({
            "module": mm.fields.String(required=True),
            "as": mm.fields.String(required=False)
        })
    ), required=False, data_key=ty.ATTR_IMPORT)


class Module:
    """A ZOTI-YAML module wraps a document with metadata and a bunch of
    utilities used for convenient data access and manipulation.

    The basic constructor requires the (possibly pre-stored)
    *preamble* and *doc* trees (see :meth:`to_dump`).

    """
    name: str
    path: Path
    preamble: Dict
    doc: Dict

    def __init__(self, preamble={}, doc={}):
        err = PreambleSchema().validate(preamble)
        if err:
            raise ImportError(pformat(err))
        self.name = preamble[ty.ATTR_MODULE]
        self.path = preamble.get(ty.ATTR_PATH, ".")
        self.preamble = preamble
        self.doc = doc

    @classmethod
    def from_zoml(cls, stream, filepath: str, key_nodes: List = []):
        """:class:`Module` constructor which incoprorates both file loader and
        parser.

        :param stream: input stream (e.g., file or stdin)

        :param filepath: mandatory identifier for source of
          input. Used in debug and error handling.

        :param tool: optional identifier for tool downstream. Used in
          logging.

        :param key_nodes: nodes whose children will be marked with
          positional info.

        """
        # print(key_nodes)
        docs = list(load(stream, path=filepath, Loader=ZomlLoader, key_nodes=key_nodes))
        # print(docs)
        if len(docs) != 2:
            msg = f"File '{filepath}' is not a ZOTI-YAML module."
            raise ImportError(msg)
        preamble, content = (ty.clean(docs[0]), docs[1])
        err = PreambleSchema().validate(preamble)
        if err:
            msg = f"Error in preamble of {filepath}:\n"
            msg += pformat(err)
            raise ImportError(msg)

        preamble[ty.ATTR_PATH] = filepath
        # if "tool-log" not in preamble:
        #     preamble["tool-log"] = []
        # preamble["tool-log"].append([str(datetime.now()), tool])
        return cls(preamble, content)

    def map_doc(self, f, with_path=False, **kwargs):
        """Functor on a Module document. Maps function *f(n)* on each node *n*
        in the document tree. If *with_path* is set to True, it
        expects function to be of form *f(n, path)* where *path* is
        this node's path relative to the document root (see
        :class:`TreePath`).'

        """

        def _get_name(node, idx):
            return (node[ty.ATTR_NAME]
                    if isinstance(node, dict) and ty.ATTR_NAME in node
                    else idx)

        def _map(f, node, path=None):
            if isinstance(node, dict):
                node = {
                    k: _map(f, v, path.with_key(k) if path else None)
                    for k, v in node.items()
                }
            elif isinstance(node, list):
                node = [
                    _map(f, v, path.with_name(_get_name(v, i)) if path else None)
                    for i, v in enumerate(node)
                ]
            elif isinstance(node, ty.Attach):
                node.ref = _map(f, node.ref, path)
            elif isinstance(node, ty.Default):
                node.original = {
                    k: _map(f, v, path.with_key(k) if path else None)
                    for k, v in node.original.items()
                }
            elif isinstance(node, ty.MergePolicy):
                raise ValueError("!policy:... construct outside !default")
            return f(node, path=path, **kwargs) if path else f(node, **kwargs)

        if with_path:
            root = ty.TreePath("/") if with_path else None
            self.doc = _map(f, self.doc, root)
        else:
            self.doc = _map(f, self.doc)

    def get(self, ref_path: Union[ty.TreePath, PurePosixPath, str], strict=True):
        """Returns an arbitrary node in the document tree vased on its path
        relative to the document root (see :class:`TreePath`). The
        path is formed like::

            /key1/key2[index2]/key3[index3]/....

        where ``keyN`` is the dictionary key of that node,
        respectively ``indexN`` can be either the index postion of the
        node in a list, or the node in a list which has a field
        ``name: indexN``.

        The *strict* argument controls whether this method throws an
        exception or returns None if the path is not found.

        *OBS*: it is the designer's responsibility to ensure that no
        two nodes in a list share the same ``name`` value.

        """
        def _get_element_with_name(nm_idx, lst, path, prev_path, key):
            try:
                try:
                    element = lst[int(nm_idx)]
                except ValueError:
                    filt = [el for el in lst
                            if isinstance(el, dict)
                            and el.get(ty.ATTR_NAME) == nm_idx]
                    element = filt[0]
            except Exception:
                if not strict:
                    return None
                else:
                    msg = f"Cannot find element with index {nm_idx}"
                    raise SearchError(msg, "/".join(prev_path))
            return _recursive_node_getter(element, path, prev_path)

        def _recursive_node_getter(obj, path: List, prev_path: List = []):
            if isinstance(obj, ty.Default):
                obj = obj.original
            try:
                if not path:
                    return obj
                key, elpath = tuple((path[0].split("[", 1) + [""])[:2])
                if not isinstance(obj, dict) or key not in obj:
                    msg = f"No '{key}' entries found"
                    raise SearchError(msg, "/".join(prev_path), obj)

                prev_path.append(path[0])
                if elpath:
                    return _get_element_with_name(
                        elpath.rstrip("]"), obj[key], path[1:], prev_path, key
                    )
                else:
                    return _recursive_node_getter(obj[key], path[1:], prev_path)
            except Exception as e:
                if not strict:
                    return None
                else:
                    raise MarkedError(e, ty.get_pos(obj))

        path = (
            ref_path if isinstance(ref_path, PurePosixPath)
            else ref_path.path if isinstance(ref_path, ty.TreePath)
            else PurePosixPath(ref_path)
        )
        parts = list(path.parts) if path.root == "" else list(path.parts)[1:]
        return _recursive_node_getter(self.doc, parts)

    def to_dump(self):
        """Returns the *preamble* and *doc* as a list suitable for storing."""
        return [self.preamble, self.doc]



class Project:
    """Handler for loading and containing a set of ZOTI-YAML modules. All
    modules are loaded relative to the roots specified by *pathvar*,
    in a similar fashion as UNIX path variables. The order of priority
    for resolving paths to module names is right-to-left.

    :param keys: list of keys to mark for storing positional metadata
      (see :doc:`syntax-reference`)

    :param pathvar: list of root paths where modules will be searched
      (see :doc:`syntax-reference`)

    :param ext: list of file extensions for searching module
      sources. Any file with another extension that specified here
      will be ignored.

    :param argfields: list of keys for fields used as placholders for,
      e.g., argument exchange. These fields will be deleted from the
      output result.

    """

    modules: Dict[str, Module]
    """dictionary of loaded modules indexed by their name"""

    def __init__(
            self,
            keys: List[str] = [],
            pathvar: List[str] = [],
            ext: List[str] = [".yaml", ".yml"],
            argfields: List[str] = ["zoti-args"],
            **kwargs
    ):
        path_var = "" if pathvar is None else pathvar
        self._load_paths = [Path(".")] + [
            Path(p) for p in reversed(path_var)
        ]
        self._key_nodes = keys
        self._exts = ext
        self._argfields = argfields
        self.modules = {}

    def resolve_path(self, name) -> Path:
        """Return a global file path where the source file for module *name*
        is found. If none found returns *FileNotFoundError*.

        """
        log.info("Searching for module: %s", name)
        for root in self._load_paths:
            fpath = Path(root, *name.split("."))
            log.info("  - in %s", fpath.as_posix())
            for ext in self._exts:
                full_path = fpath.with_suffix(ext)
                if full_path.is_file():
                    log.info("  ! found and loading %s", full_path.as_posix())
                    return full_path
        raise FileNotFoundError(f"No file found for module '{name}'")

    def load_module(self, name, source, path, with_deps: bool = True) -> None:
        """Recursively loads a (top) module with an arbitrary *name*, along
        with all its `include` dependencies declared in the modules'
        preamblies. *source* and *path* are passed to
        :class:`Module`. If *with_deps* is unset it ignores the
        `include` directives.

        """
        if isinstance(path, Path):
            path = path.as_posix()

        # resolves "!ref" entries
        def _resolve_aliases(node, aliases):
            if not isinstance(node, ty.Ref):
                return node
            if node.module in aliases:
                node.module = aliases[node.module]
            return node
        try:
            module = Module.from_zoml(source, path, self._key_nodes)
            assert path == module.path
            if name != module.name:
                msg = f"Wrong module name in preamble of {path}: "
                msg += f"expected '{name}' got '{module.name}'"
                raise ImportError(msg)

            aliases = {
                i[ty.ATTR_ALIAS]: i[ty.ATTR_MODULE]
                for i in module.preamble.get(ty.ATTR_IMPORT, [])
                if ty.ATTR_ALIAS in i
            }
            module.map_doc(_resolve_aliases, aliases=aliases)
            self.modules[name] = module
            if not with_deps:
                return
            for dep in module.preamble.get(ty.ATTR_IMPORT, []):
                if dep[ty.ATTR_MODULE] not in self.modules:
                    dep_name = dep[ty.ATTR_MODULE]
                    dep_path = self.resolve_path(dep_name)
                    with open(dep_path) as f:
                        self.load_module(dep_name, f, dep_path)
        except ModuleError as e:
            raise e
        except Exception as e:
            raise ModuleError(e, module=name, path=path)

    def build(self, name: str) -> None:
        """Parses and resolves module *name*."""
        assert name in self.modules
        log.info(" ** Building module %s", name)
        restart = True

        # stitches nodes referenced with "!attach"
        def _stitch_and_resolve(node, path):
            nonlocal restart
            try:
                if isinstance(node, ty.Attach):
                    restart = True
                    return node.resolve(self.modules)
                elif isinstance(node, ty.Ref):
                    node.resolve(this=name, root=path)
                    return node
                return node
            except Exception as e:
                msg = (node.pos.show() + "\n" if node.pos else "") + str(e)
                raise ModuleError(msg, module=name,
                                  path=self.modules[name].path)

        # resolves default values specified with "!default"
        def _postproc(node):
            try:
                if isinstance(node, ty.Default):
                    return node.resolve()
                if isinstance(node, dict):
                    for key in self._argfields:
                        if key in node:
                            del node[key]
                return node
            except Exception as e:
                raise ModuleError(e, module=name, path=self.modules[name].path)

        while restart:
            log.info("  * (re)starting the tree build...")
            restart = False
            self.modules[name].map_doc(_stitch_and_resolve, with_path=True)

        log.info("  * post-processing the tree...")
        self.modules[name].map_doc(_postproc)
