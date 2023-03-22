#!/usr/bin/env python3

import sys
import inspect
import argparse
import pathlib
import itertools
import string
import json
import importlib

from dfl import ftn, jsftn


NODE_FILE_EXT = '.dfg'
TYPE_FILE_EXT = '.ftn'

(TRIG_STATUS_NONE,
 TRIG_STATUS_EMPTY_PULSE,
 TRIG_STATUS_VALUE) = range(3)

MAP_TRIG_STATUS = {
    TRIG_STATUS_NONE:        'none',
    TRIG_STATUS_EMPTY_PULSE: 'empty-pulse',
    TRIG_STATUS_VALUE:       'value'
}

FLOW_FWD_CONTINUOUS = 'continuous'
FLOW_FWD_PARTIAL = 'partial'

SECTION_NAME = 'name'
SECTION_DESCRIPTION = 'description'
SECTION_NODES = 'nodes'
SECTION_EDGES = 'edges'
SECTION_DEFAULTS = 'defaults'

EDGE_ATTR_FLOW_NAME = 'DFL-flow-name'
EDGE_ATTR_DEFAULTS = 'DFL-defaults'

NODE_SLICE_NAME_PARAM = 'DFL-INTR-node-slice'
NODE_SLICE_NAME_DFLT = '<MAIN>'

CONSTRUCTOR_ROLE = 'constructor'
CONSTRUCTOR_MODULE = 'constructor'

COMP_KERN_ROLE = 'compute-kernel'
COMP_KERN_MODULE = 'compute_kernel'

SUBFLOW_ROLE = 'subflow'
SUBFLOW_MODULE = 'subflow'

INTRINSICS_TOPIC = 'basic'
INTRINSICS_PKG = 'dfl.intrinsics'
INTRINSICS_SPEC_CLASS = 'IntrinsicHandler'

TYPE_PKG_INHERIT = '<inherit>'

DEFAULT = '<default>'

debug_printing = False

def debug(msg):
    if debug_printing:
        print(msg)

def fatal(msg):
    sys.stderr.write('Error: {}\n'.format(msg))
    sys.exit(1)


class Epsilon(object):
    '''Internal marker class representing the empty set.'''
    pass


class Frame(object):
    def __init__(self, parent_frame, node=None, name=None):
        assert node or name
        assert parent_frame or node
        self._parent_frame = parent_frame
        self._name = name
        self._node = None
        self.set_node(node)
        self._path_names = None
        self._path_id = None
        self._children = {}
        if parent_frame:
            parent_frame._add_child_frame(self, bool(node))

    def __str__(self):
        return self.get_path_str()

    def get_parent_frame(self):
        return self._parent_frame

    def is_top_frame(self):
        return not self._parent_frame

    def get_child_by_name(self, name, create=False):
        child = self._children.get(name)
        if create and not child:
            child = Frame(self, name=name)
        return child

    def get_child_by_node(self, node, create=False):
        child = self._children.get(node.get_name())
        if create and not child:
            child = Frame(self, node=node)
        return child

    def _add_child_frame(self, child, verify_node=False):
        if verify_node:
            assert self._node
            assert self._node.get_nodedef().get_subnode(child.get_name())
        child_name = child.get_name()
        assert child_name not in self._children
        self._children[child_name] = child

    def get_name(self):
        return self._name

    def get_node(self, resolve=False):
        if resolve and not self._node:
            parent_node = self._parent_frame.get_node(resolve=True)
            self._node = parent_node.get_subnode(self._name)
        return self._node

    def set_node(self, node):
        if node == self._node:
            return
        assert not self._node
        name = node.get_name()
        if self._name:
            assert name == self._name
        self._node = node
        self._name = name

    def get_path(self):
        if self._parent_frame:
            ancestors = self._parent_frame.get_path()
        else:
            ancestors = []
        return ancestors + [self]

    def get_path_names(self):
        if self._path_names is None:
            if self._parent_frame:
                parent_names = self._parent_frame.get_path_names()
            else:
                parent_names = []
            self._path_names = parent_names + [self._name]
        return self._path_names

    def get_path_str(self, delim='^'):
        return delim.join(self.get_path_names())

    def get_path_id(self):
        if not self._path_id:
            self._path_id = self.get_path_str()
        return self._path_id

    def find_frame(self, path):
        assert path[0] == self._name
        frame = self
        for name in path[1:]:
            frame = frame.get_child_by_name(name, create=True)
        return frame


class ParameterInterpolator(string.Formatter):
    '''Resolves variables within a node's assigned parameter value.

    When definining a node prototype (called Main Prototype in the following
    text), part of it is declaring the nodes for the sub-graph within. These are
    instances of other prototypes (called Sub-Prototypes in the following).
    When doing this we may assign values to declared parameters of the
    Sub-Prototypes, but the assignment is of course only recorded in the
    instance. The Sub-Prototype itself may not be altered as it may be used
    in other places. The assigned value may however refer to parameters of the
    Main Prototype (remember, the value is defined by the Main Prototype) and
    the values of these parameters we do not known until this Main Prototype in
    turn is instantiated (which also may be done in several places), and maybe
    not even then because that value in turn may contain parameter references.
    In the end the value of a parameter may be dependent on the entire path to
    the top-level graph, which is what a chain of Frames describes.

    This class resolves these parameter references by traversing up the given
    chain of Frames. Note however that this is _not_ the same as searching for
    a binding in the usual sense, like in a hierachy of namespaces. A parameter
    reference is only looked up in the instance of the prototype. The assigned
    value may in turn have parameter references, but that is one level up.
    I.e. bindings may be hierarchical, but only as explicit references one
    level up at the time.
    '''
    def __init__(self, frame, ignore_default=False):
        super().__init__()
        self._frame = frame
        self._ignore_default = ignore_default

    def get_value(self, key, args, kwargs):
        dflt = kwargs['dflt']
        aux_params = kwargs.get('DFL_aux_params', {})
        if key in aux_params:
            return aux_params[key]
        if not self._frame:
            return dflt
        return self.get_parameter(key, dflt=dflt)

    def get_parameter(self, name, dflt=None):
        node = self._frame.get_node()
        if self._ignore_default:
            dflt = Epsilon
        v = node.get_parameter(name, dflt)
        if v is Epsilon:
            raise KeyError(name)
        if isinstance(v, str):
            frame_parent = self._frame.get_parent_frame()
            if frame_parent or not self._ignore_default:
                pi = ParameterInterpolator(frame_parent,
                                           ignore_default=self._ignore_default)
                v = pi.format(v, dflt=dflt)
        return v


class FlowEdge(object):
    def __init__(self, src_node, src_port, dst_node, dst_port,
                 attrs, node_def, context):
        self._src_node = src_node
        self._src_port = src_port
        self._dst_node = dst_node
        self._dst_port = dst_port
        self._attrs = attrs
        self._cycle = attrs.get('cycle', False)
        self._node_def = node_def
        self._context = context
        self._flow_name = None

    def __str__(self):
        return '{}:{} -> {}:{}' \
            .format(self._src_node, self._src_port.get_name(),
                    self._dst_node, self._dst_port.get_name())

    def get_flow_name(self, derive=True):
        if self._flow_name is None:
            flow_name = self.get_attr(EDGE_ATTR_FLOW_NAME, dflt=None)
            if flow_name is None and derive:
                flow_name = self._src_node.get_flow_name()
            self._flow_name = flow_name
        return self._flow_name

    def get_context(self):
        return self._context

    def get_nodedef(self):
        return self._node_def

    def get_src_node(self):
        return self._src_node

    def get_dst_node(self):
        return self._dst_node

    def get_src_port(self):
        return self._src_port

    def get_dst_port(self):
        return self._dst_port

    def get_attrs(self):
        return self._attrs

    def has_attr(self, name, incl_dflt=True):
        if name in self._attrs:
            return True
        if incl_dflt and EDGE_ATTR_DEFAULTS in self._attrs:
            defaults = self._attrs.get(EDGE_ATTR_DEFAULTS, {})
            if name in defaults:
                return True
        return False

    def get_attr(self, name, dflt=None):
        if name in self._attrs:
            return self._attrs[name]
        if EDGE_ATTR_DEFAULTS in self._attrs:
            defaults = self._attrs.get(EDGE_ATTR_DEFAULTS, {})
            if name in defaults:
                return defaults[name]
        return dflt

    def set_attr(self, name, value):
        self._attrs[name] = value

    def remove_attr(self, name):
        if name in self._attrs:
            del self._attrs[name]

    def remove_attrs(self, names):
        for n in names:
            self.remove_attr(n)

    def in_cycle(self):
        return self._cycle

    def get_context(self):
        return self._context

    def check_types(self, frame):
        if self._src_port.get_type(frame) != self._dst_port.get_type(frame):
            fatal('"{}", type mismatch for ports of edge: {}'
                  .format(self._node_def.get_spec_path(), self))
            

class Type(object):
    def __init__(self, name, module, def_str, definition, context):
        self._name = name
        self._module = module
        self._def_str = def_str
        self._definition = definition
        self._context = context
        self._is_special_type = False

        ####if not name:
        ####    self._name = definition.get_name()

    def __eq__(self, other):
        assert False, 'No reasonable implementation at the moment'
        if not isinstance(other, Type):
            return False
        if other._is_special_type:
            return other.__eq__(self)
        return self._module == other._module and self._name == other._name

    def is_same(self, other):
        # TODO: Just comparing the definition string is not a good way to
        #   judge if two types are equal, but it is easy for now. The slightly
        #   better approach of comparing the structure is not completely
        #   satisfying either, because two types maybe should be regarded
        #   incompatible if they express different things (e.g. as with
        #   new type and new subtype in Ada), but we do not have a way to
        #   express that in current FTN.
        if not isinstance(other, Type):
            return False
        if other._is_special_type != self._is_special_type:
            return False
        ####if self._name:
        ####    return self._module == other._module and self._name == other._name
        return self._def_str == other._def_str
        # return self._definition == other._definition

    def get_module(self):
        assert False, 'No reasonable implementation at the moment'
        return self._module

    ####def get_name(self):
    ####    return self._name

    def _get_fqname(self):
        if self._module:
            return self._module.get_name() + '.' + self._name
        else:
            return self._name

    def get_fqname(self):
        assert False, 'No reasonable implementation at the moment'
        if self._module:
            return self._module.get_name() + '.' + self._name
        else:
            return self._name

    def get_key(self):
        if self._name:
            return self._get_fqname()
        return self.get_def_str()

    def get_def_str(self):
        return self._def_str

    def get_definition(self):
        return self._definition


class AnyType(Type):
    def __init__(self, context):
        super().__init__('<ANY>', None, None, None, context)
        self._is_special_type = True

    def __eq__(self, other):
        assert isinstance(other, Type)
        return True


class Port(object):
    def __init__(self, port_node, parent_node_def, context):
        self._id = 'p{}'.format(context.next_unique_nr())
        context.register_obj(self._id, self)

        self._port_node = port_node
        assert isinstance(parent_node_def, NodeDef)
        self._parent_node_def = parent_node_def
        self._context = context

        self._name = port_node.get_name()
        self._node_slice_name = port_node.get_parameter(NODE_SLICE_NAME_PARAM,
                                                        NODE_SLICE_NAME_DFLT)

    def get_id(self):
        return self._id

    def __str__(self):
        return '{}:{}'.format(self._parent_node_def.get_name(), self.get_name())

    def __lt__(self, other):
        return self._name < other._name

    def get_name(self):
        return self._name

    def get_flow_name(self):
        return self._port_node.get_flow_name()

    def get_node_slice_name(self):
        return self._node_slice_name

    def is_outport(self):
        return not self.is_inport()

    def get_type(self, frame):
        '''Return the data-type the port accepts.

        Note, a port is part of a prototype node which can be instantiated
        several times, each possibly with a new specification of the actual
        types. So the type of a port is dependent on how it has been navigated
        to, i.e. dependent on the current chain of Frames, and we need to
        resolve the type within that context. The given chain
        contains the path down to the prototype node, but not the port node
        itself. Therefore the port node is appended before doing the parameter
        interpolation.
        '''
        ######## subframe = frame.get_child_by_node(self.get_port_node(), create=True)
        ######## pi = ParameterInterpolator(subframe)
        ######## type_expr = pi.get_parameter('data-type', dflt='<ANY>')
        #### type_expr = self.get_port_node() \
        ####                 .resolve_parameter(frame, 'data-type', dflt='<ANY>')
        #### if type_expr == '<ANY>':
        ####     typ = AnyType(self._context)
        #### else:
        ####     print('FTN expr: frame={}'.format(frame))
        ####     print('  type_expr={!r}'.format(type_expr))
        ####     pre_imports = \
        ####         self._parent_node_def.resolve_type_package_names(frame)
        ####     ftn_expr = dfl.ftn_lib.FtnExpr(type_expr, pre_imports,
        ####                                    self._context)
        ####     ftn_expr.process_expr()
        ####     print('  _spec={!r}'.format(ftn_expr._spec))
        ####     typ = Type(None, None, type_expr, ftn_expr.get_spec(), self._context)
        #### return typ
        return self.get_port_node() \
                   .resolve_parameter_into_type(frame, 'data-type', dflt='<ANY>')

    def get_node_def(self):
        return self._parent_node_def

    def get_port_node(self):
        return self._port_node


# TODO: Timers are handled analogous to sockets so there should not be any
#   timer ports anymore. Check this and remove.
class TimerPort(Port):
    def __init__(self, port_node, parent_node_def, context):
        super().__init__(port_node, parent_node_def, context)

    def is_inport(self):
        return True

    def get_period(self, frame):
        '''Return the period with which the timer should trigger.
        '''
        subframe = frame.get_child_by_node(self)
        pi = ParameterInterpolator(subframe)
        period = pi.get_parameter('period')
        return period


class InPort(Port):
    def __init__(self, port_node, parent_node_def, context):
        super().__init__(port_node, parent_node_def, context)

    def is_inport(self):
        return True


class OutPort(Port):
    def __init__(self, port_node, parent_node_def, context):
        super().__init__(port_node, parent_node_def, context)

    def is_inport(self):
        return False


class NodeInstance(object):
    '''An instance of a NodeDef.'''
    def __init__(self, name, parent, node_def, parameters, context):
        self._id = 'ni{}'.format(context.next_unique_nr())
        context.register_obj(self._id, self)

        self._name = name
        self._parent = parent
        assert isinstance(node_def, NodeDef)
        self._node_def = node_def
        self._parameters = parameters.copy()
        self._parameters['node-name'] = name
        self._context = context
        self._top_frame = Frame(None, self)
        self._flow_name = None

    def __str__(self):
        return '{}({})'.format(self._name, self._node_def.get_name())

    def is_system_node(self):
        return self._node_def.is_system_nodedef()

    def get_id(self):
        return self._id

    def get_name(self):
        return self._name

    def _derive_flow_name(self):
        flow_name = self.get_parameter('flow-name', dflt=None)
        if flow_name is None:
            for edge_in in self.get_connected_edges_in():
                candidate = edge_in.get_flow_name(derive=False)
                if candidate is not None:
                    if flow_name is None:
                        flow_name = candidate
                    else:
                        assert candidate == flow_name
        if flow_name is None:
            flow_name = self._name
        return flow_name

    def get_flow_name(self):
        if self._flow_name is None:
            self._flow_name = self._derive_flow_name()
        return self._flow_name

    #### TODO: This is not really needed because the Frame object can be used
    ####   direcly. Remove it when all uses have been verified to work without
    ####   it.
    ####def get_fqname(self, frame):
    ####    return frame.get_stack_str()

    def get_parent_graph(self):
        return self._parent

    #### TODO: Replaced by Frame objects, which are created in a different way.
    ####   Remove when all uses have been verfied to work without it.
    ####def get_bstack(self, bstack):
    ####    return bstack+[(self._name, self)]

    #### TODO: Should use Frame objects instead, but should not create a new
    ####   hierarchy of those, I think. Should a node instance have a Frame
    ####   hierarchy describing its full hierachy? When that is instantiated
    ####   within another NodeDef a new hierachy need to be created, so in
    ####   that case a kind of copy of the local hierachy would have to be
    ####   created, one for each instance. Need some thinking.
    ####def find_node_w_stack(self, nav_path, bstack):
    ####    return self.get_nodedef().find_node_w_stack(nav_path, bstack)

    def get_nodedef(self):
        return self._node_def

    def get_parameters(self):
        return self._parameters

    def get_parameter(self, name, dflt=None):
        return self._parameters.get(name, dflt)

    def set_parameter(self, name, value):
        self._parameters[name] = value

    def resolve_parameter(self, frame, name, dflt=None):
        '''Same as get_parameter but resolves references to parent nodes.
        '''
        nodeframe = frame.get_child_by_node(self, create=True)
        pi = ParameterInterpolator(nodeframe)
        return pi.get_parameter(name, dflt=dflt)

    def resolve_parameter_into_type(self, frame, name, dflt=None):
        type_expr = self.resolve_parameter(frame, name, dflt=dflt)
        return self.get_context().resolve_type_expr(type_expr)

    def resolve_atom_names(self, frame):
        atom_defs = self.get_nodedef().get_atom_defs()
        nodeframe = frame.get_child_by_node(self, create=True)
        aux_params = {
            'frame-path': nodeframe.get_path_str()
        }
        pi = ParameterInterpolator(nodeframe, ignore_default=True)
        return [pi.format(a, dflt=None, DFL_aux_params=aux_params)
                for a in atom_defs]

    def get_context(self):
        return self._context

    def get_top_frame(self):
        return self._top_frame

    def get_intrinsics_handler(self, topic=INTRINSICS_TOPIC):
        return self.get_nodedef().get_intrinsics_handler(topic)

    def get_inport(self, port_name, required=True):
        return self.get_nodedef().get_inport(port_name, required=required)

    def get_inports(self, sort=False):
        return self.get_nodedef().get_inports(sort=sort)

    def get_outport(self, port_name, required=True):
        return self.get_nodedef().get_outport(port_name, required=required)

    def get_outports(self, sort=False):
        return self.get_nodedef().get_outports(sort=sort)

    def get_connected_edges(self):
        if not self._parent:
            return []
        return self._parent.get_edges_for_node(self)

    def get_connected_edges_in(self):
        if not self._parent:
            return []
        return self._parent.get_edges_to_node(self)

    def get_connected_edges_to_port(self, port):
        if not self._parent:
            return []
        return self._parent.get_edges_to_port(self, port)

    def get_connected_edges_to_ports(self, ports):
        if not self._parent:
            return []
        return self._parent.get_edges_to_ports(self, ports)

    def get_connected_edges_out(self):
        if not self._parent:
            return []
        return self._parent.get_edges_from_node(self)

    def get_connected_edges_from_port(self, port):
        if not self._parent:
            return []
        return self._parent.get_edges_from_port(self, port)

    def get_connected_edges_from_ports(self, ports):
        if not self._parent:
            return []
        return self._parent.get_edges_from_ports(self, ports)


class NodeDef(object):
    '''The definition of a node type, similar to a class.

    This is instantiated into NodeInstances when building graphs. Contrary to
    classes in object-oriented systems there is no inheritance for these node
    definitions.

    Note that part of the definition of a node is a sub-graph which is built
    with NodeInstances (of other NodeDefs, of course) and FlowEdges.
    '''

    DEF_TYPE = 'NodeDef'

    def __init__(self, name, context, spec=None):
        super().__init__()
        self._id = 'nd{}'.format(context.next_unique_nr())
        context.register_obj(self._id, self)

        self._name = name
        self._context = context
        if context._is_creating_system_objects():
            self._is_system_object = True
            self._spec = spec
            self._roles = {'intrinsic', 'SYSTEM_OBJECT', name}
            self._atom_specs = []
            self._subnodes = context.get_omnipresent()
        else:
            self._is_system_object = False
            if spec is None:
                spec = context.get_repo().get_def(self.DEF_TYPE, self.get_name())
            self._spec = spec
            self._roles = None
            self._atom_specs = None
            self._subnodes = None
        self._inports = None
        self._outports = None
        self._edges = None
        self._compute_kernel_specs = None
        self._flow_forwarding = None
        self._intrinsics_handler = {}

        self._type_package_names = None

        # Pre-load specified type packages.
        # self._type_package_names = self._spec.get_field('type-packages',
        #                                                 dflt=[])
        # for tp in self._type_package_names:
        #     context.get_type_module(tp)

    def __str__(self):
        return self._name

    def is_system_nodedef(self):
        return self._is_system_object

    def _set_system_ports(self, inports, outports):
        self._inports = inports
        self._outports = outports

    def get_id(self):
        return self._id

    def get_name(self):
        return self._name

    def set_name(self, name):
        self._name = name

    def get_context(self):
        return self._context

    def get_spec(self):
        return self._spec

    def get_raw_spec(self):
        return self._spec.get_spec()

    def get_flow_forwarding(self):
        if self._flow_forwarding is None and not self._is_system_object:
            self._flow_forwarding = \
                self._spec.get_field('flow-forwarding',
                                     dflt=FLOW_FWD_CONTINUOUS)
        return self._flow_forwarding

    #### def get_type_package_names(self):
    ####     if self._type_package_names is None and not self._is_system_object:
    ####         self._type_package_names = \
    ####             self._spec.get_field('type-packages', dflt=[])
    ####     return self._type_package_names

    #### def resolve_type_package_names(self, frame):
    ####     print('resolve_type_package_names: frame={}'.format(frame))
    ####     names = self.get_type_package_names().copy()
    ####     print('    names={}'.format(names))
    ####     if TYPE_PKG_INHERIT in names:
    ####         parent_frame = frame.get_parent_frame()
    ####         parent_node = parent_frame.get_node(resolve=True)
    ####         parent_nodedef = parent_node.get_nodedef()
    ####         names.extend(parent_nodedef.resolve_type_package_names(parent_frame))
    ####         print('      continuing w frame={}'.format(frame))
    ####         print('    extended names={}'.format(names))
    ####     unique_names = {n  for n in names  if n != TYPE_PKG_INHERIT}
    ####     return list(unique_names)

    def get_atom_defs(self):
        if self._atom_specs is None:
            self._atom_specs = self._spec.get_field('atoms', [])
        return self._atom_specs

    def get_roles(self):
        if self._roles is None:
            self._roles = set(self._spec.get_field('roles', []))
        return self._roles

    def has_role(self, role):
        return role in self.get_roles()

    def has_roles(self, roles):
        node_roles = self.get_roles()
        for req in roles:
            try:
                r, should_have = req
            except:
                r = req
                should_have = True
            if (r in node_roles) != bool(should_have):
                return False
        return True

        # for r in roles:
        #     if r not in self.get_roles():
        #         return False
        # return True

    def is_intrinsic(self):
        return self.has_role('intrinsic')

    def is_divisible(self):
        return not bool(self.get_intrinsics_handler(INTRINSICS_TOPIC))

    #### TODO: See find_node_w_stack() in NodeInstance.
    ####def find_node_w_stack(self, nav_path, bstack):
    ####  name = nav_path[0]
    ####  node = self.get_subnode(name)
    ####  new_stack = node.get_bstack(bstack)
    ####  if len(nav_path) > 1:
    ####      return node.find_node_w_stack(nav_path[1:],
    ####                                    new_stack)
    ####  else:
    ####      return new_stack

    def get_subnode(self, name):
        return self._get_subnodes()[name]

    def get_subnode_frame(self, name, parent_frame):
        n = self._get_subnodes()[name]
        assert isinstance(n, NodeInstances)
        return parent_frame.get_child_by_node(n, create=True)

    def get_subnodes(self, include_system=True):
        if self._is_system_object:
            return []
        if include_system:
            return self._get_subnodes().values()
        return [ n
                 for n in self._get_subnodes().values()
                 if not n.is_system_node() ]

    def get_subnode_frames(self, parent_frame):
        return [ parent_frame.get_child_by_node(n, create=True)
                 for n in self._get_subnodes().values() ]

    def get_subnodes_matching(self, key, value):
        res = []
        for n in self._get_subnodes().values():
            spec = n.get_nodedef().get_spec()
            if spec.get_field(key) == value:
                res.append(n)
        return res

    def get_subnodes_w_roles(self, roles):
        return [ ni
                 for ni in self._get_subnodes().values()
                 if ni.get_nodedef().has_roles(roles) ]

    def _get_subnodes(self):
        if self._subnodes is None and not self._is_system_object:
            self._create_subnodes()
        return self._subnodes

    def get_inport(self, port_name, required=True):
        self._ensure_ports()
        if required:
            return self._inports[port_name]
        return self._inports.get(port_name)

    def get_inports(self, sort=False):
        self._ensure_ports()
        ports = list(self._inports.values())
        if sort:
            ports.sort()
        return ports

    def get_outport(self, port_name, required=True):
        self._ensure_ports()
        if required:
            return self._outports[port_name]
        return self._outports.get(port_name)

    def get_outports(self, sort=False):
        self._ensure_ports()
        ports = list(self._outports.values())
        if sort:
            ports.sort()
        return ports

    def get_spec_path(self):
        return self._spec.get_source()

    def get_edges(self):
        if self._edges is None and not self._is_system_object:
            self._create_edges()
        return self._edges

    def get_edges_for_node(self, node):
        assert isinstance(node, NodeInstance)
        return [ e
                 for e in self.get_edges()
                 if e.get_src_node() == node or e.get_dst_node() == node ]

    def get_edges_to_node(self, node):
        assert isinstance(node, NodeInstance)
        return [ e
                 for e in self.get_edges()
                 if e.get_dst_node() == node ]

    def get_edges_to_port(self, node, port):
        assert isinstance(port, Port)
        return [ e
                 for e in self.get_edges()
                 if e.get_dst_node() == node and e.get_dst_port() == port ]

    def get_edges_to_ports(self, node, ports):
        assert all([isinstance(p, Port) for p in ports])
        return [ e
                 for e in self.get_edges()
                 if e.get_dst_node() == node and e.get_dst_port() in ports ]

    def get_edges_from_node(self, node):
        assert isinstance(node, NodeInstance)
        return [ e
                 for e in self.get_edges()
                 if e.get_src_node() == node ]

    def get_edges_from_port(self, node, port):
        assert isinstance(port, Port)
        return [ e
                 for e in self.get_edges()
                 if e.get_src_node() == node and e.get_src_port() == port ]

    def get_edges_from_ports(self, node, ports):
        assert all([isinstance(p, Port) for p in ports])
        return [ e
                 for e in self.get_edges()
                 if e.get_src_node() == node and e.get_src_port() in ports ]

    def add_edge(self, edge):
        if self._edges is None:
            self._create_edges()
        self._edges.append(edge)

    def remove_edges_for_node(self, node):
        if self._edges is None:
            self._create_edges()
        self._edges = [ e
                        for e in self._edges
                        if e.get_src_node() != node and e.get_dst_node() != node ]

    def remove_edge(self, edge):
        assert self._edges is not None
        self._edges.remove(edge)

    def get_compute_kernel_specs(self):
        if self._compute_kernel_specs is None and not self._is_system_object:
            self._create_compute_kernel_specs()
        return self._compute_kernel_specs

    def get_compute_kernel_port_names(self, name):
        return self.get_compute_kernel_specs().get(name)

    def add_subnode(self, subnode_name, subnode):
        assert not self._is_system_object
        self._subnodes[subnode_name] = subnode
        self._update_ports(subnode)

    def remove_subnode(self, subnode_name):
        assert not self._is_system_object

        subnode = self._subnodes[subnode_name]
        subdef = subnode.get_nodedef()
        assert not (subdef.has_roles(['end-point', 'input']) or
                    subdef.has_roles(['end-point', 'output'])), \
            'Internal inconsistency: graph.py currently does not support ' \
            'removing port nodes.'

        del self._subnodes[subnode_name]

    def generate_spec(self):
        spec_def = self.get_raw_spec().copy()
        spec_def['name'] = self.get_name()

        nodes = []
        for n in self.get_subnodes():
            if n.is_system_node():
                continue
            subnode_def = n.get_nodedef()
            nodes.append([n.get_name(), subnode_def.get_name(),
                          n.get_parameters()])
        spec_def['nodes'] = nodes

        edges = []
        for e in self.get_edges():
            endp_specs = {}
            for endp, node, port in \
                [('src', e.get_src_node(), e.get_src_port()),
                 ('dst', e.get_dst_node(), e.get_dst_port())]:

                if node.is_system_node():
                    endp_specs[endp] = node.get_name()
                else:
                    endp_specs[endp] = '{}:{}'.format(node.get_name(),
                                                      port.get_name())

            spec = [endp_specs['src'], endp_specs['dst']]
            attrs = e.get_attrs()
            if attrs and EDGE_ATTR_DEFAULTS in attrs:
                attrs = attrs.copy()
                del attrs[EDGE_ATTR_DEFAULTS]
            if attrs:
                spec.append(attrs)
            edges.append(spec)
        spec_def['edges'] = edges
        return spec_def

    def get_intrinsics_handler(self, topic=INTRINSICS_TOPIC):
        inited, handler = self._intrinsics_handler.get(topic, (False, None))
        if not inited:
            mod_name = None
            if self.has_role(COMP_KERN_ROLE):
                mod_name = COMP_KERN_MODULE
            elif self.has_role(SUBFLOW_ROLE):
                mod_name = SUBFLOW_MODULE
            elif self.has_role(CONSTRUCTOR_ROLE):
                mod_name = CONSTRUCTOR_MODULE
            elif self.is_intrinsic():
                mod_name = self.get_name()
            if mod_name:
                pkg_name = self._context.get_instrinsics_package(topic)
                full_name = pkg_name + '.' + mod_name
                pkg_spec = importlib.util.find_spec(full_name)
                if pkg_spec is None:
                    fatal('Cannot find intrinsics module for {} under ' \
                          'topic {!r}'
                          .format(self.get_name(), topic))
                module = importlib.import_module(full_name)
                intrinsics_cls = getattr(module, INTRINSICS_SPEC_CLASS)
                debug('Creating intrinsics handler {} for {}' \
                      .format(full_name, self.get_name()))
                handler = intrinsics_cls(self, self._context)
            else:
                debug('No intrinsics handler obj created for {}' \
                      .format(self.get_name()))
                handler = None
            self._intrinsics_handler[topic] = (True, handler)
        return handler

    def _create_subnodes(self):
        assert not self._is_system_object
        debug('List of nodes from raw spec: {!r}'.format(self._spec['nodes']))
        cls = self._context.get_ext_class(NodeInstance)
        self._subnodes = self._context.get_omnipresent().copy()
        for n in self._spec['nodes']:
            node_def = self._context.get_node_def(n[1])
            inst = cls(n[0], self, node_def, n[2], self._context)
            self._subnodes[n[0]] = inst

    def _update_ports(self, new_subnode):
        if self._outports is None:
            # Ports have not yet been created so it does not matter if
            # new_subnode is a port or not.
            return

        if new_subnode.get_nodedef().has_roles(['end-point', 'input']):
            inport_cls = self._context.get_ext_class(InPort)
            self._inports[new_subnode.get_name()] = \
                inport_cls(new_subnode, self, self._context)
        elif new_subnode.get_nodedef().has_roles(['end-point', 'output']):
            outport_cls = self._context.get_ext_class(OutPort)
            self._outports[new_subnode.get_name()] = \
                outport_cls(new_subnode, self, self._context)


    def _ensure_ports(self):
        if self._outports != None or self._is_system_object:
            return

        ###timer_port_cls = self._context.get_ext_class(TimerPort)
        inport_cls = self._context.get_ext_class(InPort)
        outport_cls = self._context.get_ext_class(OutPort)

        #### timer_ports = {}
        #### timer_nodes = self.get_subnodes_w_roles(['end-point', 'timer'])
        #### for ni in timer_nodes:
        ####     timer_ports[ni.get_name()] = timer_port_cls(ni, self, self._context)
        #### self._timer_ports = timer_ports

        inports = {}
        input_nodes = self.get_subnodes_w_roles(['end-point', 'input'])
        for ni in input_nodes:
            inports[ni.get_name()] = inport_cls(ni, self, self._context)
        self._inports = inports

        outports = {}
        output_nodes = self.get_subnodes_w_roles(['end-point', 'output'])
        for ni in output_nodes:
            outports[ni.get_name()] = outport_cls(ni, self, self._context)
        self._outports = outports

        # input_nodes = self.get_subnodes_matching('border-node', 'input')
        # self._inports = {ni.get_name(): inport_cls(ni, self, self._context)
        #                  for ni in input_nodes}

        # subflow_input_nodes = self.get_subnodes_matching('border-node',
        #                                                  'subflow-input')
        # self._subflow_inports = \
        #     {ni.get_name(): inport_cls(ni, self, self._context)
        #      for ni in subflow_input_nodes}

        # outport_cls = self._context.get_ext_class(OutPort)
        # output_nodes = self.get_subnodes_matching('border-node', 'output')
        # self._outports = {ni.get_name(): outport_cls(ni, self, self._context)
        #                   for ni in output_nodes}

        # subflow_output_nodes = self.get_subnodes_matching('border-node',
        #                                                   'subflow-output')
        # self._subflow_outports = \
        #     {ni.get_name(): outport_cls(ni, self, self._context)
        #      for ni in subflow_output_nodes}

    def _create_edges(self):
        edge_defaults = self._spec.get_field('defaults', {}).get('edges')
        edges = []
        edge_cls = self._context.get_ext_class(FlowEdge)
        for e in self._spec['edges']:
            debug('e={}'.format(repr(e)))
            nodes = {}
            ports = {}
            for endp, idx, dr in [('src', 0, 'out'), ('dst', 1, 'in')]:
                node_name, _, port_name = e[idx].partition(":")
                try:
                    node = self.get_subnode(node_name)
                except KeyError:
                    fatal('"{}", "{}" not defined among nodes'
                          .format(self.get_spec_path(), node_name))
                if node.is_system_node():
                    port_name = node_name
                try:
                    if dr == 'out':
                        port = node.get_nodedef().get_outport(port_name)
                    else:
                        port = node.get_nodedef().get_inport(port_name)
                except KeyError:
                    fatal('"{}", no {}-port "{}" in node "{}"'
                          .format(self.get_spec_path(), dr, port_name, node_name))
                nodes[endp] = node
                ports[endp] = port
            attrs = {} if len(e) <= 2 else e[2]
            if edge_defaults:
                attrs[EDGE_ATTR_DEFAULTS] = edge_defaults
            new_edge = edge_cls(nodes['src'], ports['src'],
                                nodes['dst'], ports['dst'],
                                attrs, self, self._context)
            edges.append(new_edge)
        self._edges = edges

    def _create_compute_kernel_specs(self):
        self._compute_kernel_specs = \
            { n: (i, o)
              for n,i,o in self._spec.get_field('compute-kernels', []) }


class Context(object):
    def __init__(self, search_paths=None, ftn_ctxt=None):
        super().__init__()
        self._unique_numbers = itertools.count(start=1, step=1)
        self._creating_system_objects = False
        self._node_defs = {}
        self._sys_nodes = {}
        self._sys_inports = {}
        self._sys_outports = {}
        self._repo = FileRepo(search_paths)
        self._obj_register = {}
        self._intrinsics_packages = { INTRINSICS_TOPIC: INTRINSICS_PKG }

        if ftn_ctxt is None:
            ftn_ctxt = (jsftn.FtnContext, {})
        self._ftn_ctxt_class, self._ftn_ctxt_kwargs = ftn_ctxt
        self._ftn_context = None

        ELEMENT_CLASSES = [
            FlowEdge, Type, AnyType,
            Port, TimerPort, InPort, OutPort,
            NodeInstance, NodeDef
        ]
        self._element_classes = {}
        cls_hierarchy = inspect.getmro(self.__class__)
        module_hierarchy = [sys.modules[cls.__module__] for cls in cls_hierarchy]
        for mod in module_hierarchy:
            for base_class in ELEMENT_CLASSES:
                if base_class in self._element_classes:
                    # We have already found the most specific subclass for this.
                    continue

                classes = [ cls for cls in mod.__dict__.values()
                            if isinstance(cls, type)
                            and issubclass(cls, base_class)
                            and cls.__name__ == base_class.__name__]
                assert len(classes) <= 1
                if len(classes) == 1:
                    cls = classes[0]
                    debug('Found {}.{} for base class {}.{}'
                          .format(cls.__module__, cls.__name__,
                                  base_class.__module__, base_class.__name__))
                    self._element_classes[base_class] = cls

        self._creating_system_objects = True
        for name in ['SYSTEM', 'DROP']:
            nodedef = self.create_node_def(name, {})

            cls = self.get_ext_class(NodeInstance)
            node = cls(name, None, nodedef, {}, self)
            self._sys_nodes[name] = node

            cls = self.get_ext_class(InPort)
            inport = cls(node, nodedef, self)
            self._sys_inports[name] = inport
            inports = {name: inport}

            if name == 'DROP':
                outports = {}
            else:
                cls = self.get_ext_class(OutPort)
                outport = cls(node, nodedef, self)
                self._sys_outports[name] = outport
                outports = {name: outport}

            nodedef._set_system_ports(inports, outports)
        self._creating_system_objects = False

    def _is_creating_system_objects(self):
        return self._creating_system_objects

    def get_omnipresent(self):
        return self._sys_nodes

    def get_repo(self):
        return self._repo

    def get_ext_class(self, cls):
        return self._element_classes[cls]

    def append_search_path(self, path):
        self._repo.append_search_path(path)

    def append_search_path_str(self, pathstr):
        self._repo.append_search_path_str(pathstr)

    def prepend_search_path(self, path):
        self._repo.prepend_search_path(path)

    def prepend_search_path_str(self, pathstr):
        self._repo.prepend_search_path_str(pathstr)

    def get_instrinsics_package(self, topic):
        return self._intrinsics_packages[topic]

    def add_intrinsics_package(self, topic, pkg_name):
        self._intrinsics_packages[topic] = pkg_name

    def find_file(self, fname, exts=None):
        return self._repo.find_file(fname, exts)

    def next_unique_nr(self):
        return next(self._unique_numbers)

    def get_ftn_context(self):
        if not self._ftn_context:
            search_paths = self._repo.get_search_paths()
            kwargs = self._ftn_ctxt_kwargs.copy()
            kwargs['search_paths'] = search_paths
            self._ftn_context = self._ftn_ctxt_class(**kwargs)
        return self._ftn_context

    def get_obj(self, obj_id):
        return self._obj_register[obj_id]

    def register_obj(self, obj_id, obj):
        self._obj_register[obj_id] = obj

    def resolve_type_expr(self, type_expr):
        if type_expr == '<ANY>':
            cls = self.get_ext_class(AnyType)
            typ = cls(self)
        else:
            ftn_ctxt = self.get_ftn_context()
            type_spec = ftn_ctxt.expr2type(type_expr)
            cls = self.get_ext_class(Type)
            typ = cls(None, None, type_expr, type_spec, self)
        return typ

    def create_node_def(self, name, spec=None):
        assert not self._node_defs.get(name)
        if spec is None:
            spec = {
                'name': name,
                'nodes': [],
                'edges': []
            }
        spec_obj = Spec(name, spec)
        cls = self.get_ext_class(NodeDef)
        node_def = cls(name, self, spec=spec_obj)
        self._node_defs[name] = node_def
        return node_def

    def get_node_def(self, name, create=True):
        node_def = self._node_defs.get(name)
        if not node_def and create:
            cls = self.get_ext_class(NodeDef)
            node_def = cls(name, self)
            self._node_defs[name] = node_def
        return node_def

    def load_node_def(self, name):
        node_def = self.get_node_def(name)
        return node_def

    def load_node(self, node_name):
        node_def = self.load_node_def(node_name)
        cls = self.get_ext_class(NodeInstance)
        node = cls(node_name, None, node_def, {}, self)
        return node

    def load_node_file(self, pathstr):
        path = pathlib.Path(pathstr)
        if path.suffix != NODE_FILE_EXT:
            fatal('path "{}" missing required suffix "{}"'
                  .format(pathstr, NODE_FILE_EXT))
        self.prepend_search_path(path.parent)
        return self.load_node(path.stem)


class Spec(object):
    def __init__(self, source, spec):
        self._source = source
        self._spec = spec

    def get_source(self):
        return self._source

    def get_spec(self):
        return self._spec

    def has_field(self, fld):
        return fld in self._spec

    def get_field(self, fld, dflt=None):
        return self._spec.get(fld, dflt)

    def __getitem__(self, fld):
        return self._spec[fld]


class FileRepo(object):
    def __init__(self, search_paths=None):
        super().__init__()
        self._search_paths = []
        if search_paths:
            for p in search_paths:
                self.append_search_path_str(p)

    def get_search_paths(self):
        return self._search_paths

    def append_search_path(self, path):
        self._search_paths.append(path)

    def append_search_path_str(self, pathstr):
        self.append_search_path(pathlib.Path(pathstr))

    def prepend_search_path(self, path):
        self._search_paths.insert(0, path)

    def prepend_search_path_str(self, pathstr):
        self.prepend_search_path(pathlib.Path(pathstr))

    def find_file(self, fname, exts=None):
        if not exts:
            exts = ['']
        for sp in self._search_paths:
            for ext in exts:
                p = sp / (fname + ext)
                if p.is_file():
                    return p

    def get_def(self, def_type, def_name):
        assert def_type == NodeDef.DEF_TYPE

        fname = def_name + NODE_FILE_EXT
        fp = self.find_file(fname)
        if not fp:
            fatal('Cannot find file {}'.format(fname))
        with fp.open('r') as f:
            try:
                return Spec(fp, json.load(f))
            except json.decoder.JSONDecodeError as e:
                fatal('"{}", {}'.format(fp, e))


def main():
    argparser = argparse.ArgumentParser(description='Parses JSON file and builds internal structure.')
    argparser.add_argument('--flow', '-F', required=True,
                           help='name of input flow')
    argparser.add_argument('--search-path', '-I', action='append',
                           help='adds path to search for flow def files')
    argparser.add_argument('--debug', action='store_true',
                           help='turn on debug printouts')
    args = argparser.parse_args()

    global debug_printing
    debug_printing = args.debug

    ctxt = Context(search_paths=args.search_path)
    graph = ctxt.load_node(args.flow)

if __name__ == '__main__':
    main()
