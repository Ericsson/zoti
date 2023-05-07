import logging as log
from pathlib import Path
from typing import Dict, List

import zoti_yaml.core as ty
from zoti_yaml.exceptions import ModuleError
from zoti_yaml.module import Module


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
        """Return a global path where the source file for module *name* is
        found. If none found returns *FileNotFoundError*.

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
        """Reecursively loads a (top) module with an arbitrary *name*, along
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
