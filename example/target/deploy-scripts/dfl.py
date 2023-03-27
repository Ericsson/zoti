#!/usr/bin/env python3

import sys
import inspect
import argparse
import pathlib
import itertools
import string
import json

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


    def get_src_node(self):
        return self._src_node

    def get_dst_node(self):
        return self._dst_node

    def get_src_port(self):
        return self._src_port

    def get_dst_port(self):
        return self._dst_port

    # def get_attrs(self):
    #     return self._attrs

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

    def get_name(self):
        return self._name



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

    def get_nodedef(self):
        return self._node_def

    def get_parameter(self, name, dflt=None):
        return self._parameters.get(name, dflt)

    def set_parameter(self, name, value):
        self._parameters[name] = value

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

    def get_inports(self, sort=False):
        return self.get_nodedef().get_inports(sort=sort)

    def get_outports(self, sort=False):
        return self.get_nodedef().get_outports(sort=sort)


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

    def is_intrinsic(self):
        return self.has_role('intrinsic')


    def get_subnode(self, name):
        return self._get_subnodes()[name]

    def get_subnodes(self, include_system=True):
        if self._is_system_object:
            return []
        if include_system:
            return self._get_subnodes().values()
        return [ n
                 for n in self._get_subnodes().values()
                 if not n.is_system_node() ]

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

    def _create_subnodes(self):
        assert not self._is_system_object
        debug('List of nodes from raw spec: {!r}'.format(self._spec.get_field('nodes')))
        cls = self._context.get_ext_class(NodeInstance)
        self._subnodes = self._context.get_omnipresent().copy()
        for n in self._spec.get_field('nodes', []):
            node_def = self._context.get_node_def(n[1])
            inst = cls(n[0], self, node_def, n[2], self._context)
            self._subnodes[n[0]] = inst

    def _ensure_ports(self):
        if self._outports != None or self._is_system_object:
            return

        ###timer_port_cls = self._context.get_ext_class(TimerPort)
        inport_cls = self._context.get_ext_class(InPort)
        outport_cls = self._context.get_ext_class(OutPort)

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

    def _create_edges(self):
        edge_defaults = self._spec.get_field('defaults', {}).get('edges')
        edges = []
        edge_cls = self._context.get_ext_class(FlowEdge)
        for e in self._spec.get_field('edges', []):
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
                    # fatal('"{}", no {}-port "{}" in node "{}"'
                    #       .format(self.get_spec_path(), dr, port_name, node_name))

                    nodedef = self._context.create_node_def(port_name, {})
                    cls = self._context.get_ext_class(NodeInstance)
                    p_node = cls(port_name, node, nodedef, {}, self._context)
                    if dr == 'out':
                        cls = self._context.get_ext_class(OutPort)
                        port = cls(p_node, nodedef, self._context)
                        if self._outports is None:
                            self._outports = {}
                        self._outports[port_name] = port
                    else:
                        cls = self._context.get_ext_class(InPort)
                        port = cls(p_node, nodedef, self._context)
                        if self._inports is None:
                            self._inports = {}
                        self._inports[port_name] = port
                    
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

        # ELEMENT_CLASSES = [
        #     FlowEdge, Type, AnyType,
        #     Port, TimerPort, InPort, OutPort,
        #     NodeInstance, NodeDef
        # ]
        ELEMENT_CLASSES = [
            FlowEdge, 
            Port, InPort, OutPort,
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


    def next_unique_nr(self):
        return next(self._unique_numbers)


    def register_obj(self, obj_id, obj):
        self._obj_register[obj_id] = obj

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

    # def has_field(self, fld):
    #     return fld in self._spec

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
            # fatal('Cannot find file {}'.format(fname))
            return Spec(fp, {})
        with fp.open('r') as f:
            try:
                return Spec(fp, json.load(f))
            except json.decoder.JSONDecodeError as e:
                fatal('"{}", {}'.format(fp, e))
