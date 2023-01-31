from datetime import datetime
from pathlib import Path, PurePosixPath
from pprint import pformat
from typing import Dict, List, Union

import marshmallow as mm

import zoti_yaml.core as ty
from zoti_yaml.exceptions import MarkedError, SearchError
from zoti_yaml.loader import ZotiLoader, load


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
    """Module"""
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
    def from_zoml(cls, stream, filepath: str, tool="", key_nodes: List = []):
        # print(key_nodes)
        docs = list(load(stream, path=filepath, tool=tool,
                         Loader=ZotiLoader, key_nodes=key_nodes))
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
        if "tool-log" not in preamble:
            preamble["tool-log"] = []
        preamble["tool-log"].append([str(datetime.now()), tool])
        return cls(preamble, content)

    def map_doc(self, f, with_path=False, **kwargs):
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
            elif isinstance(node, ty.WithCreate):
                raise ValueError("!with_create construct outside !default")
            elif isinstance(node, ty.WithReplace):
                raise ValueError("!with_replace construct outside !default")
            return f(node, path=path, **kwargs) if path else f(node, **kwargs)

        if with_path:
            root = ty.TreePath("/") if with_path else None
            self.doc = _map(f, self.doc, root)
        else:
            self.doc = _map(f, self.doc)

    def get(self, ref_path: Union[ty.TreePath, PurePosixPath, str], strict=True):
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
        return [self.preamble, self.doc]
