import logging as log
from pathlib import Path
from typing import Dict, Optional
from importlib.metadata import distribution

import yaml
from yaml.loader import SafeLoader
from yaml.nodes import MappingNode, SequenceNode, ScalarNode

import zoti_yaml.core as ty


class LoaderWithInfo(SafeLoader):
    def __init__(self, stream, **kwargs):
        path = getattr(stream, "name")
        self._path = Path(path) if path else None
        self._isfile = self._path and self._path.is_file()
        self._tool = None
        self._key_nodes = []
        super(LoaderWithInfo, self).__init__(stream)

    def construct_mapping(self, node, deep=False):
        """Override SafeLoader to add positional information for mappings."""
        mapping = super(LoaderWithInfo, self).construct_mapping(node, deep=deep)

        if not self._isfile:
            return mapping

        # below is a hack: alter the 'node' object to communicate to
        # future calls of this method to add the 'mark_for_meta' entry.
        for key, value in zip(mapping.keys(), node.value):
            if key in self._key_nodes:
                if isinstance(value[1], SequenceNode):
                    for obj in value[1].value:
                        if isinstance(obj, MappingNode):
                            setattr(obj, "mark_for_meta", True)
                elif isinstance(value[1], MappingNode):
                    for obj in value[1].value:
                        if isinstance(obj[1], MappingNode):
                            setattr(obj[1], "mark_for_meta", True)

        # here check previously altered 'node' entry
        if hasattr(node, "mark_for_meta"):
            for key, value in zip(mapping.keys(), node.value):
                if key == ty.INFO:
                    mapping[ty.INFO] = super(
                        LoaderWithInfo, self).construct_mapping(value[1], deep=True)
            ty.attach_pos(mapping, ty.Pos.from_mark(
                node.start_mark, node.end_mark, self._path.as_posix(), self._tool))
        return mapping


class ZomlLoader(LoaderWithInfo):
    """YAML loader class with extra spices."""

    def __init__(self, stream, key_nodes=[], **kwargs):
        super(ZomlLoader, self).__init__(stream)
        self._tool = distribution("zoti_yaml").name + "-" + distribution("zoti_yaml").version
        self._key_nodes = key_nodes


    def include(self, node):
        """One can import raw (chunks of) files using the the ``!include``
        command. It should be used to attach entire source code to
        entries of certain nodes. Usage:

        .. code-block:: yaml

            !include {file: path/relative/to/module.ext}
            !include {file: path/relative/to/module.ext, name: block_name}
            !include {file: path/relative/to/module.ext, begin: (keyword|number), end: (keyword|number)}

        In the first case an entire file is included as raw text. In
        the second case it extracts the portion of text between the
        lines containing ``BEGIN block_name`` and ``END
        block_name``. In the third case the start and stop lines are
        specified either as line numbers or by arbitrary keywords.

        """

        def full_file(path):
            with open(path, "r") as f:
                return f.read()

        def between_indexes(path, begin, end):
            with open(path, "r") as f:
                lines = f.readlines()[begin - 1: end]
                return "".join(lines)

        def between_markers(path, begin, end):
            with open(path, "r") as f:
                content = f.readlines()
                lines, storing = ([], False)
                for line in content:
                    if line.startswith(end):
                        if storing:
                            return "".join(lines)
                        else:
                            raise ValueError(
                                "End marker found before begin marker")
                    if storing:
                        lines.append(line)
                    if line.startswith(begin):
                        storing = True
                raise ValueError("Did not find markers")

        args = self.construct_mapping(node)
        try:
            path = self._path.parent.joinpath(args["file"])
            if "name" in args:
                return between_markers(
                    path, f"BEGIN {args['name']}", f"END {args['name']}"
                )
            elif "begin" in args and "end" in args:
                try:
                    return between_indexes(path, int(args["begin"]),
                                           int(args["end"]))
                except Exception:
                    return between_markers(path, args["begin"], args["end"])
            else:
                return full_file(path)

        except Exception as e:
            raise yaml.MarkedYAMLError(
                problem="Cannot extract text pointed by !include call",
                problem_mark=node.start_mark,
                note=str(e),
            )

    def construct_ref(self, node):
        try:
            return ty.Ref(**self.construct_mapping(node, deep=True))
        except Exception as e:
            raise yaml.MarkedYAMLError(
                note=str(e), problem_mark=node.start_mark)

    def construct_attach(self, node):
        try:
            mapping = self.construct_mapping(node, deep=True)
            pos = ty.Pos.from_mark(node.start_mark, node.end_mark,
                                   self._path.as_posix(), self._tool)
            return ty.Attach(pos=pos, **mapping)
        except Exception as e:
            raise yaml.MarkedYAMLError(
                note=str(e), problem_mark=node.start_mark)

    def construct_default(self, node):
        try:
            return ty.Default(*self.construct_sequence(node))
        except Exception as e:
            raise yaml.MarkedYAMLError(
                note=str(e), problem_mark=node.start_mark)

    def construct_any(self, node, deep=False):
        if isinstance(node, ScalarNode):
            return self.construct_scalar(node)
        elif isinstance(node, SequenceNode):
            return self.construct_sequence(node, deep=deep)
        elif isinstance(node, MappingNode):
            return self.construct_mapping(node, deep=deep)
        assert False

    def construct_policy_union(self, node):
        try:
            return ty.MergePolicy.from_keyword(ty.POLICY_UNION, self.construct_any(node))
        except Exception as e:
            raise yaml.MarkedYAMLError(
                note=str(e), problem_mark=node.start_mark)

    def construct_policy_runion(self, node):
        try:
            return ty.MergePolicy.from_keyword(ty.POLICY_RUNION, self.construct_any(node))
        except Exception as e:
            raise yaml.MarkedYAMLError(
                note=str(e), problem_mark=node.start_mark)

    def construct_policy_inter(self, node):
        try:
            return ty.MergePolicy.from_keyword(ty.POLICY_INTER, self.construct_any(node))
        except Exception as e:
            raise yaml.MarkedYAMLError(
                note=str(e), problem_mark=node.start_mark)

    def construct_policy_rinter(self, node):
        try:
            return ty.MergePolicy.from_keyword(ty.POLICY_RINTER, self.construct_any(node))
        except Exception as e:
            raise yaml.MarkedYAMLError(
                note=str(e), problem_mark=node.start_mark)


ZomlLoader.add_constructor("!include", ZomlLoader.include)
ZomlLoader.add_constructor("!default", ZomlLoader.construct_default)
ZomlLoader.add_constructor("!attach", ZomlLoader.construct_attach)
ZomlLoader.add_constructor("!ref", ZomlLoader.construct_ref)
ZomlLoader.add_constructor(f"!policy:{ty.POLICY_UNION}", ZomlLoader.construct_policy_union)
ZomlLoader.add_constructor(f"!policy:{ty.POLICY_RUNION}", ZomlLoader.construct_policy_runion)
ZomlLoader.add_constructor(f"!policy:{ty.POLICY_INTER}", ZomlLoader.construct_policy_inter)
ZomlLoader.add_constructor(f"!policy:{ty.POLICY_RINTER}", ZomlLoader.construct_policy_rinter)


def load(stream, Loader, **kwargs):
    loader = Loader(stream, **kwargs)
    try:
        while loader.check_data():
            yield loader.get_data()
    except yaml.MarkedYAMLError as e:
        raise e
    finally:
        loader.dispose()
