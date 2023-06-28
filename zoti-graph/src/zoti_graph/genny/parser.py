import logging as log
import marshmallow as mm
import zoti_yaml as zoml

from zoti_graph.core import ATTR_KIND, ATTR_NAME, META_UID, KEY_NODE, KEY_PORT, KEY_PRIM
import zoti_graph.genny.core as ty
from zoti_graph.appgraph import AppGraph
from zoti_graph.core import Uid
from zoti_graph.exceptions import ParseError, ValidationError

__zoti__ = AppGraph("genny")


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


##########
## EDGE ##
##########


class EdgeParser(mm.Schema):
    """An edge connects two node ports and represents a data communication
    medium. It can be described using the fields below:

    ``edge_type:`` <obj>
      raw dictionary containing information about the transmission
      medium relevant for generating glue code for it. It is passed
      as-is to the tools downstream.

    ``connect:`` <list>
      a 4-tuple containing information about the edge connection:

      1. <path> to node where the edge originates, relative to this
         edge's parent node.

      2. name of port belonging to the source node. If the source is
         a primitive node then this place is declared ``none``.

      3. <path> to node where the edge is destined, relative to this
         edge's parent node.

      4. name of port belonging to the destination node. If the
         destination is a primitive node then this place is declared
         ``none``.

    """

    _info = mm.fields.Mapping(data_key=zoml.INFO, load_default={})
    mark = mm.fields.Mapping(load_default={})
    connect = mm.fields.Tuple(
        (
            mm.fields.String(required=True, allow_none=False),
            mm.fields.String(required=True, allow_none=True),
            mm.fields.String(required=True, allow_none=False),
            mm.fields.String(required=True, allow_none=True),
        )
    )
    edge_type = mm.fields.Mapping(load_default={})

    @mm.post_load
    def pmake(self, data, **kwargs):
        try:
            edge = ty.Edge(**data)
            connect = data["connect"]
            src, dst = (Uid(connect[0]), Uid(connect[2]))
            if connect[1] is not None:
                src = src.withPort(connect[1])
            if connect[3] is not None:
                dst = dst.withPort(connect[3])
            return (edge, src, dst)
        except Exception as e:
            raise ParseError(e, zoml.get_pos(data))

    @mm.pre_dump
    def pdump(self, obj, **kwargs):
        return vars(obj)


##########
## PORT ##
##########


class PortParser(mm.Schema):
    """A port is the conduit between a node and an edge and carries
    various functional and behavioral information relevant to
    different abstractions. It is defined using the following
    attributes:

    ``name:`` <str> *required*
      A unique identifier within the scope of its parent node.

    ``kind:`` <str> *required*
      The port kind (in, out, side). In and out ports represent event
      ports triggering connected nodes within the same timeline. Side
      ports stand for side-effects, and do not trigger their nodes,
      i.e. connected nodes may be part of different timelines.

    ``port_type:`` <obj>
      Raw dictionary containing behavioral information relevant when
      generating access glue. If not provided, it should be filled in
      by a port inference mechanism further down in the processing
      pipeline (e.g. ZOTI-Tran).

    ``data_type:`` <obj>
      Raw data passed to a type system for generating type glue
      (e.g. ZOTI-FTN). If not provided, it should be inferred using a
      port inference mechanism further down in the processing pipeline
      (e.g., ZOTI-Tran)

    """

    _info = mm.fields.Mapping(data_key=zoml.INFO, load_default={})
    uid = mm.fields.Raw(required=True, data_key=META_UID)
    mark = mm.fields.Mapping(load_default={})
    name = mm.fields.String(required=True)
    kind = mm.fields.String(required=True)
    port_type = mm.fields.Mapping(load_default={})
    data_type = mm.fields.Mapping(load_default={})

    @mm.post_load
    def pmake(self, data, **kwargs):
        try:
            data["kind"] = ty.Dir[data["kind"]]
            port = ty.Port(**data)
            __zoti__.new(data["uid"], port)
            return data["uid"]
        except Exception as e:
            raise ParseError(e, zoml.get_pos(data))

    @mm.pre_dump
    def pdump(self, obj, **kwargs):
        ret = vars(obj)
        ret["kind"] = ret["kind"].name
        return ret


###########
## NODES ##
###########

class NodeChoiceField(mm.fields.Field):
    def _deserialize(self, node, attr, data, **kwargs):
        try:
            if node is None:
                return None
            if ATTR_KIND not in node:
                ret = CompositeNodeParser().load(node)
            elif node[ATTR_KIND] == "CompositeNode":
                ret = CompositeNodeParser().load(node)
            elif node[ATTR_KIND] == "SkeletonNode":
                ret = SkeletonNodeParser().load(node)
            elif node[ATTR_KIND] == "PlatformNode":
                ret = PlatformNodeParser().load(node)
            elif node[ATTR_KIND] == "ActorNode":
                ret = ActorNodeParser().load(node)
            elif node[ATTR_KIND] == "KernelNode":
                ret = KernelNodeParser().load(node)
            elif node[ATTR_KIND] == "BasicNode":
                ret = BasicNodeParser().load(node)
            else:
                raise ValueError(f"Node kind not recognized '{node['kind']}'")
            return ret
        except mm.ValidationError as error:
            if zoml.get_pos(node):
                error.messages = [str(zoml.get_pos(node)), error.messages]
            raise error

    def _serialize(self, value, attr, obj, **kwargs):
        # print("!!!!!!", type(value), value.name)
        if isinstance(value, ty.CompositeNode):
            ret = CompositeNodeParser().dump(value)
            ret[ATTR_KIND] = "CompositeNode"
        elif isinstance(value, ty.SkeletonNode):
            ret = SkeletonNodeParser().dump(value)
            ret[ATTR_KIND] = "SkeletonNode"
        elif isinstance(value, ty.PlatformNode):
            ret = PlatformNodeParser().dump(value)
            ret[ATTR_KIND] = "PlatformNode"
        elif isinstance(value, ty.ActorNode):
            ret = ActorNodeParser().dump(value)
            ret[ATTR_KIND] = "ActorNode"
        elif isinstance(value, ty.KernelNode):
            ret = KernelNodeParser().dump(value)
            ret[ATTR_KIND] = "KernelNode"
        elif isinstance(value, ty.BasicNode):
            ret = BasicNodeParser().dump(value)
            ret[ATTR_KIND] = "BasicNode"
        else:
            raise ValueError(f"Wrong serialization type {type(value)}")
        return ret


class NodeParser(mm.Schema):
    """A node is the base entity in ZOTI-Graph. All nodes, regardless of
    their type, may have the following entries:

    ``name``: <str> *required*
      node name. Needs to be unique within the scope of its parent.

    ``kind:`` <str>
      denotes the type of node, see `Node Kinds`_. Default
      ``CompositeNode``.

    ``description``: <str>
      free-form text.

    ``mark``: <dict>

      free-form dictionary, markings passed as-is to graph
      transformer. Similar to ``parameters`` but should become
      obsolete after the transformation phase and should not be passed
      to the code generator,

    ``parameters``: <dict>

      free-form dictionary of parameters passed as-is to the code
      generator. Similar to ``mark``, but should not be touched during
      transformation, but rather handed over to the code generator.

    ``nodes``: `nodes`_
      list of child node entries

    ``ports``: `ports`_
      list of ports for this node

    ``edges``: `edges`_
      list of edges connecting children's ports between them or with
      their parent (this node's ports)

    """

    # internal (unexposed) key
    uid = mm.fields.Raw(required=True, data_key=META_UID)
    _info = mm.fields.Mapping(data_key=zoml.INFO, load_default={})

    # keys that have already been used but are here for validation only
    description = mm.fields.String()
    node_type = mm.fields.String(
        data_key=ATTR_KIND,
        load_default="CompositeNode",
        validate=mm.validate.OneOf(
            ["CompositeNode", "PlatformNode", "ActorNode",
             "SkeletonNode", "KernelNode", "BasicNode"]
        ),
    )

    # useful keys
    mark = mm.fields.Mapping(load_default={})  # TODO: redundant?
    name = mm.fields.String(required=True)
    parameters = mm.fields.Mapping(load_default={}, allow_none=True)
    nodes = mm.fields.List(NodeChoiceField(), load_default=[])
    ports = mm.fields.List(Nested(PortParser), load_default=[])
    edges = mm.fields.List(Nested(EdgeParser), load_default=[])

    @mm.post_load
    def pmake(self, data, constructor, **kwargs):
        uid = data["uid"]
        node_uid = data["uid"]
        if data["parameters"] is None:
            data["parameters"] = {}
        curr_scope = data
        try:
            if len(data["nodes"]) != len(set([n for n in data["nodes"]])):
                raise KeyError(f"Node {uid} has children with duplicate names")
            if len(data["ports"]) != len(set([p for p in data["ports"]])):
                raise KeyError(f"Node {uid} has ports with duplicate names")
            node = constructor(**data)
            __zoti__.new(node_uid, node)
            for child_uid in data["nodes"]:
                __zoti__.register_child(node_uid, child_uid)
                log.info(f" - registered node {child_uid}")
            for port_uid in data["ports"]:
                __zoti__.register_port(node_uid, port_uid)
                log.info(f" - registered port {port_uid}")
            for edge, src, dst in data["edges"]:
                curr_scope = edge
                src_id = node_uid.withPath(src)
                dst_id = node_uid.withPath(dst)
                __zoti__.connect(src_id, dst_id, edge)
                log.info(f" - connected {src_id} -> {dst_id}")
            return uid
        except Exception as e:
            raise ParseError(e, zoml.get_pos(curr_scope))

    @mm.pre_dump
    def pdump(self, obj, **kwargs):
        return {
            "mark": obj.mark,
            "name": obj.mark,
            "parameters": obj.mark,
        }


class ActorNodeParser(NodeParser):
    """An ``ActorNode`` is a behavioral computation unit, and denotes a
    (set of) reactions to the stimuli that arrive to its ports. As a
    modeling element it originates from a model of computation
    process, whose semantics are *translated* in terms of its
    detector.

    *NOTE*: the detector definition is still under development and is
    likely to change in the future.

    An actor node might contain the following special fields:

    ``detector:`` <obj>
      describes a finite state machine (FSM) that determines the
      behavior of this actor. If none is provided, the default
      behavior assumes immediate reaction and run-to-completion for
      every port triger. An FSM is defined using the fields below:

      ``inputs``: <list> *required*
        list of port names to which this actor reacts

      ``preproc:`` <str>
        points to a child (kernel) node which acts as the port
        preprocessor for the inputs mentioned above. If none is
        mentioned the inputs are used as they are.

      ``states``: <list>
        list of state names defined for this FSM. By convention the
        first state in the list is the initial state. If none
        provided, it assumes the actor has unique state, in which case
        it acts as a combinational process.

      ``scenarios:`` <dict>
        dictionary associating each state name with a child node
        implementing its scenario. Can be left empty in case of unique
        state, in which case all children constitute this actor's
        unique scenario.

      ``expr:`` <dict> *required*
        dictionary associating each state name with a certain reaction
        described using the fields below:

        ``cond:`` <str> *required*
          simple arithmetical and logical expression on the inputs
          which describes the condition that triggers a reaction and a
          state change

        ``goto:`` <str>
          state name active when the previous condition is
          fulfilled. Not necessary in case of unique state.

    """

    class FSMParser(mm.Schema):
        class ExprParser(mm.Schema):
            cond = mm.fields.String(required=True)
            goto = mm.fields.String()

        inputs = mm.fields.List(
            mm.fields.String(),
            required=True,
        )
        preproc = mm.fields.String(load_default=None)
        states = mm.fields.List(mm.fields.String(), load_default=None)
        scenarios = mm.fields.Mapping(
            keys=mm.fields.String(), values=mm.fields.String(), load_default=None
        )
        expr = mm.fields.Mapping(
            keys=mm.fields.String(), values=mm.fields.Nested(ExprParser), required=True
        )

        @mm.post_load
        def pmake(self, data, **kwargs):
            return ty.ActorNode.FSM(**data)

        @mm.pre_dump
        def pdump(self, obj, **kwargs):
            return vars(obj)

    detector = mm.fields.Nested(FSMParser)

    @mm.post_load
    def pmake(self, data, **kwargs):
        return super(ActorNodeParser, self).pmake(data, constructor=ty.ActorNode)

    @mm.pre_dump
    def pdump(self, obj, **kwargs):
        return vars(obj)


class CompositeNodeParser(NodeParser):
    """A ``CompositeNode`` is simply a cluster of nodes. It does not have
    any semantics nor any special field and it is mainly used to group
    sub-systems into (modular) components.

    """

    @mm.post_load
    def pmake(self, data, **kwargs):
        return super(CompositeNodeParser, self).pmake(
            data, constructor=ty.CompositeNode
        )

    @mm.pre_dump
    def pdump(self, obj, **kwargs):
        return vars(obj)


class SkeletonNodeParser(NodeParser):
    """*OBS: experimental!*

    Node (cluster) that describe an implicit pattern formed using its
    child nodes. The pattern is denoted by its *type* entry. Unlike
    ``ActorNode``, this node does not imply a (trigger) behavior,
    rather a specific interconnection pattern. Obviously, this name
    needs to resolved to a certain code template by the translator.

    ``type:`` <str>
      name of pattern

    """
    type = mm.fields.String(required=True)

    @mm.post_load
    def pmake(self, data, **kwargs):
        return super(SkeletonNodeParser, self).pmake(
            data, constructor=ty.SkeletonNode
        )

    @mm.pre_dump
    def pdump(self, obj, **kwargs):
        return vars(obj)


class PlatformNodeParser(NodeParser):
    """A ``PlatformNode`` denotes a computation platform and is essential
    for determining the synthesis details. As a general rule, all
    components under a platform node will be mapped to the same target
    (e.g. binary, kernel, container or whatever the processing unit of
    the target platform is defined as) It might have the following
    special field:

    ``target:`` <obj> *required*
      information on target platform, passd as-is to the graph
      processor downstream, e.g. ZOTI-Tran

    """

    target = mm.fields.Mapping(required=True)

    @mm.post_load
    def pmake(self, data, **kwargs):
        return super(PlatformNodeParser, self).pmake(data, constructor=ty.PlatformNode)

    @mm.pre_dump
    def pdump(self, obj, **kwargs):
        return vars(obj)


class KernelNodeParser(NodeParser):
    """A ``KernelNode`` is a leaf computation node, typically representing
    a function in the target platform language. It might have the following
    special field:

    ``extern:`` <str> *required*
      Contains the full source code of the kernel as formatted
      text.

    """

    extern = mm.fields.String(required=True)

    @mm.post_load
    def pmake(self, data, **kwargs):
        return super(KernelNodeParser, self).pmake(data, constructor=ty.KernelNode)

    @mm.pre_dump
    def pdump(self, obj, **kwargs):
        return vars(obj)


class BasicNodeParser(NodeParser):
    """A ``BasicNode`` is a leaf node with a specific function in the
    target platform. Unlike a ``KernelNode``, it does not carry a
    native piece of code, and is only relevant during the
    transformation process where it might trigger a specific
    refinement. It needs to specify the following special field.

    ``type:`` <str> *required*
      the primitive type. Possible ``SYSTEM``, marking a connection to
      the outside world; ``DROP`` marks that the connection is dropping
      the data.

    **OBS:** Since BasicNodes are replaced during transformation,
    eveything passed to their ``parameters`` field will be ignored.

    """
    class Meta:
        unknown = mm.EXCLUDE

    type = mm.fields.String(required=True)

    @mm.post_load
    def pmake(self, data, **kwargs):
        return super(BasicNodeParser, self).pmake(data, constructor=ty.BasicNode)

    @mm.pre_dump
    def pdump(self, obj, **kwargs):
        return vars(obj)


def parse(*module_args) -> AppGraph:
    """Parses a complete (schema-validated) ZOTI input specification tree
    along with its metadata and returns an application graph that
    can be futher process by a ZOTI tool (e.g. ZOTI-Tran).

    *module_args* is a list of arguments passed to `zoti_yaml.Module
    <../zoti-yaml/api-reference>`_ constructor (e.g., as loaded from a
    JSON or YAML file) and should consist at least of a *preamble* and
    a *document*. The ``preamble`` argument is expected to have a
    field ``main-is`` containing the path to the top (i.e. root) node.

    **ATTENTION:** the design of this library assumes that this
    function is invoked only once per program instance. If for any
    reason you need to call it twice, any previously parsed
    application graph will be reset, so make sure you use ``deepcopy``
    in case you need to keep more application graphs in the same
    program instance.

    """
    import re
    from pathlib import PurePath, PurePosixPath

    def _add_uid(node, path):
        if not (isinstance(node, dict) and ATTR_NAME in node):
            return node
        node_key = re.sub(r'\[[^]]*\]', '', path.path.name)
        if node_key not in [KEY_NODE, KEY_PORT, KEY_PRIM]:
            return node
        try:
            parent_uid = Uid(
                PurePath(*re.findall(r'\[([^]]+)',
                         path.path.parent.as_posix()))
            )
            if node_key in [KEY_NODE, KEY_PRIM]:
                node[META_UID] = parent_uid.withNode(node[ATTR_NAME])
                log.info(f" - added uid: {node[META_UID]}")
            elif node_key == KEY_PORT:
                node[META_UID] = parent_uid.withPort(node[ATTR_NAME])
                log.info(f" - added uid: {node[META_UID]}")
            return node
        except Exception as e:
            msg = f"When processing UID of element at path {path.path.as_posix()}"
            msg += "\n" + str(e)
            raise zoml.MarkedError(msg, pos=zoml.get_pos(node))

    try:
        module = zoml.Module(*module_args)
        module.map_doc(_add_uid, with_path=True)
        main_path = PurePosixPath(module.preamble["main-is"])
        top_comp = module.get(main_path)
        __zoti__.reset(top_comp[META_UID])
        _ = CompositeNodeParser().load(top_comp)
        return __zoti__
    except mm.ValidationError as error:
        raise ValidationError(error.messages)
    except Exception as e:
        raise zoml.ModuleError(e, module=module.name, path=module.path)
