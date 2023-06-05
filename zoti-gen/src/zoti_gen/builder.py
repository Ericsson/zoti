import importlib
import types
from collections import OrderedDict
from copy import deepcopy
from typing import Dict, List, Set
import logging as log

import marshmallow as mm
from zoti_yaml import Module, get_pos

import zoti_gen.core as ty
import zoti_gen.util as util
from zoti_gen.core import Block, Label, Requirement, Template
from zoti_gen.exceptions import ModelError, ParseError, ValidationError


class Builder:
    """This handler takes care of loading input specifications, templates,
    building and dumping target code artifacts.

    :arg main: the qualified name of the main module (containing a
      ``top`` entry in preamble which points to the project's top
      block)

    :arg srcs: a list of initialized `zoti_yaml.Module
      <../zoti-yaml>`_ containing all the raw input
      specifications. Used for their qualified name queries.

    :arg annotations: `formatted string
      <https://www.w3schools.com/python/ref_string_format.asp>`_ for
      printing :class:`Block` information (before, after) the template
      expansion. In the formatting, the variable ``comp`` represents
      the current :class:`Block` object.

    """
    _mods: Dict
    _blks: Dict

    main: ty.Ref
    """ Constructed path to the top (i.e., main) block """

    requs: Requirement
    """Resolved dependencies. Available only after calling
    :meth:`resolve()`."""

    decls: List
    """ List of component declared at top level. Available only after
    calling :meth:`resolve()`."""

    def __init__(self, main: str, srcs: List[Module], annotation=(None, None)):
        # self.main = main
        self._annot_begin, self._annot_end = annotation
        self._annot_begin = f"\n{self._annot_begin}\n" if self._annot_begin else "\n"
        self._annot_end = f"\n{self._annot_end}\n" if self._annot_end else "\n"
        if not srcs:
            raise ImportError("No input sources provided.")
        modules = {mod.name: mod for mod in srcs}
        self._mods = {}
        for nm, mod in modules.items():
            self._mods[nm] = {bl[ty.ATTR_NAME]: bl
                              for bl in mod.doc[ty.ATTR_BLOCK]}
            # print(list(self._mods[nm].keys()))
            # print(list([b["name"] for b in mod.doc[ty.ATTR_BLOCK]]))
            if len(self._mods[nm].keys()) != len(mod.doc[ty.ATTR_BLOCK]):
                raise ImportError(f"Module '{nm}' contains duplicate names.")
        self._blks = {}
        assert "top" in modules[main].preamble
        self.main = ty.Ref(module=main, name=modules[main].preamble["top"])
        self.requs = Requirement({})
        self.decls = []

    def get(self, ref=None, caller=None) -> Block:
        """Gets a :class:`Block` object using its qualified name. If the the
        block has been parsed before it returns the
        previously-constructed block, otherwise it follows the
        decision flow:

             | it searches the specifications
             | if it refers to a library template
             |   | it imports the base constructor using `importlib <https://docs.python.org/3/library/importlib.html>`_
             | else
             |   | uses :class:`Block` base constructor
             | parses the specifications and constructs the block

        """

        def _get_spec(module, name):
            spec = importlib.util.find_spec(module)
            if spec is None:
                raise ImportError(f"Cannot find module '{module}'")
            # m = spec.loader.load_module(module)  # DEPRECATED!
            m = types.ModuleType(spec.loader.name)
            spec.loader.exec_module(m)
            if m is None:
                raise ImportError(f"Cannot load module '{module}'")
            if name not in vars(m):
                raise ImportError(
                    f"Spec for '{name}' not found in module '{module}'")
            return vars(m)[name]

        if ref is None:
            return Block("_DUMMY", code="", prototype=None)

        if ref in self._blks:
            return self._blks[ref]

        if ref.module in self._mods:
            if ref.name not in self._mods[ref.module]:
                msg = f"Block '{ref.name}' not found in module '{ref.module}'"
                raise ParseError(msg, caller)
            comp_src = self._mods[ref.module][ref.name]
            needs_spec = ty.ATTR_TYPE in comp_src
            if needs_spec:
                spec_ref = ty.RefSchema().load(comp_src[ty.ATTR_TYPE])
            info = comp_src if get_pos(comp_src) else caller
        else:
            comp_src = {"name": ref.name}
            needs_spec = True
            spec_ref, info = ref, caller

        try:
            if needs_spec:
                spec = _get_spec(spec_ref.module, spec_ref.name)
                comp = spec.Schema(unknown=mm.EXCLUDE).load(comp_src)
                # if storing it might overwrite wrongly
                self._blks[ref] = comp
            else:
                comp = Block.Schema().load(comp_src)
                self._blks[ref] = comp
        except mm.ValidationError as err:
            raise ValidationError(err.messages, info)

        if comp._info is None:
            comp._info = get_pos(caller)

        return comp

    def parse(self):
        """Recursively parses a loaded project (i.e., containing input
        specifications) and creates the (hidden) internal
        representation starting from the main block inwards.

        """

        log.info(f"*** Loading all components related to '{self.main}' ***")

        def _recursive(ref, caller):
            comp = self.get(ref, caller)
            log.info(f"  - Loaded '{ref}'")
            if not comp.instance:
                return
            for inst in comp.instance:
                _recursive(inst.block, caller=inst)

        _recursive(self.main, caller=None)

    def resolve(self):
        """Resolves names/bindings and renders code. OBS: alters the internal
        structure of each respective block entry."""

        log.info(f"*** Resolving bindings and expanding templates ***")

        def _check_attr(obj, *attrlist):
            missing = [attr for attr in attrlist if getattr(obj, attr) is None]
            if missing:
                msg = f"{type(obj).__name__} is missing attribute(s): {missing}"
                name = getattr(obj, "name") if hasattr(
                    obj, "name") else util.qualname(obj)
                raise ModelError(msg, name, get_pos(obj))

        def _self_check(comp, context):
            if callable(getattr(comp, ty.FUN_CHECK, None)):
                try:
                    getattr(comp, ty.FUN_CHECK)()
                except Exception as e:
                    msg = "Self-validation failed"
                    msg += f" with:\n{e}" if e else ""
                    raise ModelError(msg, comp.name, context)

        def _map_bindings(instance, labels, params):
            newlabelb = {}
            newparamb = {}

            def label_to_label(parent, child, usage, info=None):
                b_label = deepcopy(labels[parent])
                b_label.name = usage.render(
                    # CONTEXT-BEGIN: bind/label_to_label
                    p=parent,      # ID of parent
                    label=labels,  # entire namespace of resolved labels
                    param=params,  # entire namespace of parameters
                    # CONTEXT-END: bind/label_to_label
                    info=info
                )
                newlabelb[child] = b_label
                
            def param_to_label(parent, child, info=None):
                b_label = Label(name=params[parent], usage=params[parent], glue={})
                b_label.name = params[parent]
                newlabelb[child] = b_label

            def usage_to_label(child, usage, info=None):
                b_label = Label(name=usage.render(
                    # CONTEXT-BEGIN: bind/usage_to_label
                    label=labels,  # entire namespace of resolved labels
                    param=params,  # entire namespace of parameters
                    # CONTEXT-END: bind/usage_to_label
                ), usage=usage, glue={})
                newlabelb[child] = b_label

            def param_to_param(parent, child, **kwargs):
                newparamb[child] = params[parent]

            def value_to_param(child, value, **kwargs):
                newparamb[child] = value

            for bind in instance.bind:
                try:
                    locals()[bind.func](**bind.args, info=get_pos(bind))
                except Exception as e:
                    raise ModelError(e, obj=bind)

            return newlabelb, newparamb

        def _recursive_inst(inst, comp, b_labels, b_params, namespace):
            if ty.PRAGMA_EXP in inst.directive:
                log.info(f"  - Expanding instance {inst.placeholder}...")
                _check_attr(inst, ty.ATTR_PH)
                _recursive_blks(comp, b_labels, b_params, namespace)
                _check_attr(comp, ty.ATTR_CODE)
                if inst.usage:
                    log.info(f"  - Creating call code for {inst.placeholder}")
                    comp.code = inst.usage.render(
                        # CONTEXT-BEGIN: instance/usage-expand
                        name=comp.name,    # component's name
                        label=comp.label,  # resolved labels
                        param=comp.param,  # parameters
                        placeholder={      # only one placeholder
                            "code": comp.code
                        },
                        # CONTEXT-END: instance/usage-expand
                        info=get_pos(comp),
                    )
                return comp.code
            elif inst.block not in self.decls or ty.PRAGMA_NEW in inst.directive:
                # print("=============================")
                # if self.decls:
                #     print(type(self.decls[0]))
                # print(comp.name, inst.block, self.decls)
                # print("=============================")
                log.info(f"  - Making new block for instance ...")
                labels = b_labels if ty.PRAGMA_PASS in inst.directive else {}
                _recursive_blks(comp, labels, b_params, set(self.decls))
                self.decls.append(inst.block)
                _check_attr(comp, ty.ATTR_CODE, ty.ATTR_PROTO)
                comp.code = comp.prototype.render(
                    # CONTEXT-BEGIN: prototype
                    name=comp.name,    # component's name
                    label=comp.label,  # resolved labels
                    param=comp.param,  # parameters
                    placeholder={      # only one placeholder
                        "code": comp.code
                    },
                    # CONTEXT-END: prototype
                    info=get_pos(comp),
                )

                if inst.placeholder:
                    log.info(f"  - Created call code for {inst.placeholder}")
                    _check_attr(inst, ty.ATTR_USAGE)
                    return inst.usage.render(
                        # CONTEXT-BEGIN: instance/usage-noexpand
                        name=comp.name,    # component's name
                        param=comp.param,  # parameters
                        label=b_labels,    # bounded (parent) labels
                        # CONTEXT-END: instance/usage-noexpand
                        info=get_pos(comp),
                    )
                else:
                    return None
            else:
                log.info(f"  - Creating call code for {inst.placeholder}")
                return inst.usage.render(
                    name=comp.name,    # component's name
                    label=b_labels,    # bounded (parent) labels
                    param=comp.param,  # parameters
                    info=get_pos(comp),
                )

        def _recursive_blks(comp, b_labels, b_params, namespace: Set[str]):
            name = util.uniqueName(comp.name, namespace, update=True)
            log.info(f" ** Resolving component '{name}'")
            comp.name = name
            for key, label in comp.label.items():
                label.name = util.uniqueName(key, namespace, update=True)
            log.info(f"  - Updated label names for {list(comp.label.keys())}")

            params = {**comp.param, **b_params}
            log.info(f"  - Updated params {list(params.keys())}")

            labels = OrderedDict({**comp.label, **b_labels})
            for key, label in labels.items():
                if key not in b_labels:
                    _check_attr(label, ty.ATTR_USAGE)
                    label.name = label.usage.render(
                        # CONTEXT-BEGIN: label/usage
                        p=key,         # ID of the current label
                        label=labels,  # complete namespace of resolved labels
                        param=params,  # complete namespace of parameters
                        # CONTEXT-END: label/usage
                        info=get_pos(label),
                    )
            log.info(
                f"  - Updated parent label bindings {list(labels.keys())}")

            comp.param = params
            comp.label = labels

            rinst = {}
            if comp.instance:
                for inst in comp.instance:
                    rcomp = self.get(inst.block, caller=comp)
                    blabels, bparams = _map_bindings(
                        inst, comp.label, comp.param)
                    rinst[inst.placeholder] = _recursive_inst(
                        inst, rcomp, blabels, bparams, namespace
                    )

            _self_check(comp, get_pos(comp))
            if comp.requirement is not None:
                self.requs.update(comp.requirement)
                log.info(f"  - Updated global requirements")

            if isinstance(comp.code, Template):
                code = self._annot_begin.format(comp=comp)
                code += comp.code.render(
                    # CONTEXT-BEGIN: code
                    label=comp.label,   # resolved labels
                    param=comp.param,   # parameters
                    placeholder=rinst,  # recursivly-expanded block instances
                    # CONTEXT-END: code
                    info=get_pos(comp),
                )
                code += self._annot_end.format(comp=comp)
                comp.code = code
                log.info(f"  - rendered code")

        main = self.get(self.main)
        _recursive_blks(main, {}, {}, set())
        try:
            main.code = main.prototype.render(
                # CONTEXT-BEGIN: code
                name=main.name,
                label=main.label,   # resolved labels
                param=main.param,   # parameters
                placeholder={
                    "code": main.code
                },
                # CONTEXT-END: code
                info=get_pos(main),
            )
        except Exception as e:
            raise ModelError(e, "main", obj=main)
        self.decls.append(self.main)
