from collections import OrderedDict
from dataclasses import dataclass, field
from pprint import pformat
from string import Template
from typing import Dict, List, Optional

import marshmallow as mm
import networkx as nx
import zoti_yaml as zoml

ATTR_NAME = "name"
ATTR_BLOCK = "block"
ATTR_TYPE = "type"
ATTR_PH = "placeholder"
ATTR_CODE = "code"
ATTR_PROTO = "prototype"
ATTR_USAGE = "usage"

PRAGMA_PASS = "pass"
PRAGMA_NEW = "new"
PRAGMA_EXP = "expand"

FUN_CHECK = "check"           # member of library component
FUN_LTOL = "label_to_label"  # member of ProjHandler.resolve._map_bindings
FUN_UTOL = "usage_to_label"  # member of ProjHandler.resolve._map_bindings
FUN_PTOP = "param_to_param"  # member of ProjHandler.resolve._map_bindings
FUN_VTOP = "value_to_param"  # member of ProjHandler.resolve._map_bindings

KEYS_PRAGMA = [PRAGMA_PASS, PRAGMA_NEW, PRAGMA_EXP]
KEYS_BIND = [FUN_LTOL, FUN_UTOL, FUN_PTOP, FUN_VTOP]


class Nested(mm.fields.Nested):
    def __init__(self, nested, **kwargs):
        super(Nested, self).__init__(nested, **kwargs)

    def _deserialize(self, node, attr, data, **kwargs):
        try:
            return super(Nested, self)._deserialize(node, attr, data, **kwargs)
        except mm.ValidationError as error:
            if zoml.get_pos(node):
                error.messages = [str(zoml.get_pos(node)), error.messages]
            raise error


class TemplateFun:
    template: Optional[str]
    args: List[str]
    attr: str

    def __init__(self, attr, *args):
        self.attr = attr
        if len(args) == 0 or None in args:
            self.args, self.template = [], None
        elif len(args) == 1:
            self.args, self.template = [], args[0]
        else:
            self.args = list(args[:-1])
            self.template = args[-1]

    def __repr__(self):
        args = ", ".join(self.args)
        return f"({args}) -> {self.template}"

    def __bool__(self):
        return self.template is not None

    def render(self, *args, **kwargs):
        if self.template is None:
            msg = f"Cannot render empty template for field '{self.attr}'"
            raise AttributeError(msg)
        if not self.args:
            return self.template
        context = {**dict(zip(self.args, args)), **kwargs}
        return Template(self.template).substitute(context)


class TemplateFunField(mm.fields.Field):
    def _deserialize(self, node, attr, data, **kwargs):
        if not isinstance(node, list):
            raise mm.ValidationError(
                "Expected TemplateFun arguments as a list.")
        if not len(node):
            raise mm.ValidationError(
                "Expected at least one argument to TemplateFun")
        return TemplateFun(attr, *node)

    def _serialize(self, obj, attr, data, **kwargs):
        return obj.args + [obj.template]


###############
# REQUIREMENT #
###############


class Requirement:
    """
    Illustrates prerquisites. Stors input iterables (e.g., lists) as
    dependency graphs.

    :param requirement: dictionary of iterables.

    """

    requirement: Dict[str, nx.DiGraph]
    """ Dictionary of dependency graphs. """

    def __init__(self, requirement, **kwargs):
        self.requirement = {
            key: nx.path_graph(req) for key, req in requirement.items()}

    def __repr__(self) -> str:
        ret = pformat({
            key: list(graph.nodes())
            for key, graph in self.requirement.items()
        })
        return f"Requirement({ret})"

    def update(self, other: Optional["Requirement"]):
        """merges two ``Requirement`` entries updating the dependency
        graphs."""
        if other:
            for key, graph in other.requirement.items():
                if key in self.requirement:
                    self.requirement[key].update(graph)
                else:
                    self.requirement[key] = graph

    def dep_list(self, key) -> List:
        """Returns a list with the solved dependencies for a certain
        requirement type."""
        return list(nx.dfs_preorder_nodes(self.requirement[key]))

    def as_dict(self) -> Dict:
        return {key: self.dep_list(key) for key in self.requirement.keys()}


class RequirementSchema(mm.Schema):
    """Illustrates prerequisites for the parent element. It may contain
    the following entries:

    :include: a list of files or modules to be included in the
              preamble of the generated target artifact

    """

    include = mm.fields.List(mm.fields.Str())

    @mm.post_load
    def make(self, data, **kwargs):
        return Requirement(requirement=data)


############
# INSTANCE #
############

@dataclass(repr=False)
class Ref:
    module: str
    name: str

    def __repr__(self):
        return f"{self.module}.{self.name}"

    def __hash__(self):
        return hash("{self.module}{self.name}")


class RefSchema(mm.Schema):
    module = mm.fields.String(required=True)
    name = mm.fields.String(required=True)

    @mm.post_load
    def make_ref(self, data, **kwargs):
        return Ref(**data)


@dataclass
class Bind:
    func: str
    args: Dict
    _info: Dict = field(default_factory=lambda: {})


class BindSchema(mm.Schema):
    """A binding between one of the labels or parameters of the parent
    block and a label or parameter of the referenced block. It may
    contain one of the following entries:

    :label_to_label: with entries ``parent`` (str), ``child`` (str)
        and ``usage`` (`Template Function <#template-function>`_)

    :usage_to_label: with entries ``child`` (str) and ``usage``
        (`Template Function <#template-function>`_)

    :param_to_param: with entries ``parent`` (str), ``child`` (str)

    :value_to_param: with entries ``child`` (str), ``value`` (str)
    """

    label_to_label = mm.fields.Nested(
        mm.Schema.from_dict(
            {
                "parent": mm.fields.String(required=True),
                "child": mm.fields.String(required=True),
                "usage": TemplateFunField(required=False),
            }
        )
    )
    usage_to_label = mm.fields.Nested(
        mm.Schema.from_dict(
            {
                "child": mm.fields.String(required=True),
                "usage": TemplateFunField(required=False),
            }
        )
    )
    param_to_param = mm.fields.Nested(
        mm.Schema.from_dict(
            {
                "parent": mm.fields.String(required=True),
                "child": mm.fields.String(required=True),
            }
        )
    )
    value_to_param = mm.fields.Nested(
        mm.Schema.from_dict(
            {
                "child": mm.fields.String(required=True),
                "value": mm.fields.String(required=True),
            }
        )
    )
    _info = mm.fields.Raw(data_key="_info", load_default={})

    @mm.post_load
    def make(self, data, **kwargs):
        func, args = [(k, v) for k, v in data.items() if k in KEYS_BIND][0]
        return Bind(func, args, data["_info"])

    @mm.post_dump(pass_original=True)
    def dump_bind(self, obj, orig, **kwargs):
        return {orig.func: orig.args}

    @mm.validates_schema
    def validate_bind(self, data, **kwargs):
        allowed = [k for k in data.keys() if k in KEYS_BIND]
        if len(allowed) != 1:
            msg = f"Only one of the following key is allowed: {repr(KEYS_BIND)}"
            raise mm.ValidationError(msg)


@dataclass  # (init=False)
class Instance:
    """Entry binding a placeholder in the parent's template code to
    another block.

    """

    placeholder: Optional[str]
    """ ID for the template placeholder """

    block: Optional[Dict]
    """ ID of the block referenced to fill the placeholder """

    directive: List[str]

    bind: List[Bind]
    """ list of bindings between the parent block and referenced block """

    usage: TemplateFun
    """ Target-dependent template passed by type system """

    _info: Dict = field(default_factory=lambda: {})


class InstanceSchema(mm.Schema):
    """Refers to another block and (at minimum) triggers its evaluation by
    the the `Rendering <rendering>`_ engine. It can define an
    inclusion relation between the parent and the referenced blocks,
    in which case the referenced one would occupy the space pointed
    out by a *placeholder* markup in the parent's
    template. Furthermore, the relation between the two blocks can be
    enforced by a set of *bindings* that connects the labels and
    parameters of the two blocks.

    To define a block instance within the parent block the following
    entries might be used:

    :block: a `Reference <#reference>`_ entry pointing to an existing
        (i.e. loaded) block.

    :placeholder: the name of the placeholder, as it appears in the
        parent's `Code Template <#code-template>`_.

    :directive: a list of directive strings passed to the `Rendering
        <rendering>`_ engine.

    :`bind <#bind>`_: list of bindings between the labels and
        parameters of the parent block and those of the referenced block.

    :usage: a `Template Function <#template-function>`_ defining how
        this block is being instantiated in case it is not expanded inline
        (e.g., as function call). The template string is defined by the
        type system.

    """
    placeholder = mm.fields.String(required=True, allow_none=True)
    block = mm.fields.Nested(RefSchema, required=True, allow_none=True)
    directive = mm.fields.List(
        mm.fields.String(validate=mm.validate.OneOf(KEYS_PRAGMA)),
        required=False, load_default=[]
    )
    bind = mm.fields.List(Nested(BindSchema), required=False, load_default=[])
    # usage = mm.fields.String(required=False)
    usage = TemplateFunField(required=False, allow_none=True,
                             load_default=TemplateFun("instance/usage"))
    _info = mm.fields.Raw(data_key="_info", load_default={})

    @mm.post_load
    def make(self, data, **kwargs):
        return Instance(**data)


#########
# LABEL #
#########


@dataclass
class Label:
    """ Carries information about labels (filled in by type system) """

    name: str
    """ Unique name in the scope of a block"""

    usage: TemplateFun
    """ Default usage template. Called on top-level (non-binding) instances."""

    glue: Dict
    """Dictionary of templates passed from the type system."""

    _info: Dict = field(default_factory=lambda: {})


class LabelSchema(mm.Schema):
    """A label is the low-level code equivalent of a 'port'. Its function is to
    provide a name which can be used in bindings and glue generation.

    :name: unique ID in the scope of the parent block
    :usage: a `Template Function <#template-function>`_ defining how
        this label is to be expanded in the code. Provided by the type
        system.
    :glue: a dictionary of glue code tailored for various
        circumstances, provided by the type system and accessible from
        within the code template using the `label.<port_id>.glue` key.

    """
    name = mm.fields.Str(required=True)
    usage = TemplateFunField(required=True)
    glue = mm.fields.Mapping(
        keys=mm.fields.String(
            required=True,  # , validate=mm.validate.NoneOf(["name"])
        ),
        # values=TemplateFunField(),  # TODO
        values=mm.fields.Raw(),
        required=False, allow_none=True, load_default={})
    _info = mm.fields.Raw(data_key="_info", load_default={})

    @mm.post_load
    def make(self, data, **kwargs):
        return Label(**data)


class LabelListField(mm.fields.List):
    def __init__(self, **kwargs):
        self.base = Nested(LabelSchema)
        super(LabelListField, self).__init__(self.base, **kwargs)

    def _serialize(self, pdict, attr, obj, **kwargs):
        if pdict is None:
            return []
        return [
            self.base._serialize(p, attr, dict(pdict), **kwargs)
            for p in pdict.values()
        ]

    def _deserialize(self, plist, attr, data, **kwargs):
        if plist is None:
            return None
        names = [p["name"] for p in plist]
        if len(names) != len(set(names)):
            raise mm.ValidationError("Duplicate names in label list")
        return OrderedDict([
            (p["name"], self.base._deserialize(p, attr, plist, **kwargs))
            for p in plist
        ])


#########
# BLOCK #
#########


@dataclass
class Block:
    """ Base class for block structure. """

    class Schema(mm.Schema):
        """A block describes a unit of code that might be related to other
        blocks through bindings and might contain a template. Blocks
        are described using the following entries;

        :name: (mandatory) the unique ID of the block
        :type: a `Reference <#reference>`_ pointing to an
            externally-defined library template which would fill in
            the corresponding entries below, as documented in
            `Template Libraries <template-libs>`_ page.
        :`requirement <#requirement>`_: block prerequisites
        :`label <#label>`_: list of label entries, each with a unique name
        :param: a dictionary of generic parameters passed as-is to the template
            renderer, accessed with the `param` key.
        :`instance <#instance>`_: a list of other blocks somehow related to
            this one.
        :code: a string containing this block's
            `Code Template <#code-template>`_
        :prototype: a `Template Function <#template-function>`_ defining this
            block's type signature, as provided from a type system.

        """

        name = mm.fields.String(required=True)
        requirement = mm.fields.Nested(RequirementSchema)
        label = LabelListField()
        param = mm.fields.Mapping(required=False)
        code = mm.fields.String(allow_none=True)
        prototype = TemplateFunField(allow_none=True)
        instance = mm.fields.List(Nested(InstanceSchema), required=False)
        _info = mm.fields.Raw(data_key="_info", load_default={})

        @mm.post_load
        def make(self, data, **kwargs):
            return Block(**data)

    name: str
    """ Unique ID of block. """

    prototype: TemplateFun = field(default=TemplateFun("prototype"))
    """ Target dependent function signature provided by the type system """

    requirement: Optional[Requirement] = None
    """ Block prerequisites."""

    label: OrderedDict[str, Label] = field(
        default_factory=lambda: OrderedDict())
    """ Ordered dictionary of labels """

    param: Dict = field(default_factory=lambda: {})
    """ Generic parameters """

    code: Optional[str] = None
    """ Target code for block, either as Jinja template or as raw text """

    instance: List[Instance] = field(default_factory=lambda: [])
    """list of instances that bind template (code) placeholders to other
    blocks"""

    _info: Dict = field(default_factory=lambda: {})
