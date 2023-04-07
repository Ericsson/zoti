#!/usr/bin/env python3
# Copyright (C) Ericsson AB, 2019-2020
#
# The document(s) may be used, copied or otherwise distributed only with
# the written permission from Ericsson AB or in accordance with the
# terms and conditions stipulated in the agreement/contract under which
# the document(s) have been supplied.
#

import os
import sys
import time
import argparse
import pathlib
import re
import shutil
import importlib
import itertools
import socket
import json

import dfl


ATTR_EXTERNAL_NAME = 'external-name'

PORT_OFFSET_VAR = 'DFL_PORT_OFFSET'


use_csv = False
debug_printing = False

def debug(msg):
    if debug_printing:
        print(msg)

def fatal(msg):
    sys.stderr.write('Error: {}\n'.format(msg))
    sys.exit(1)


class FlowEdge(dfl.FlowEdge):
    def __init__(self, src_node, src_port, dst_node, dst_port,
                 attrs, node_def, context):
        super().__init__(src_node, src_port, dst_node, dst_port,
                         attrs, node_def, context)
        self._external_dst = None

    def resolve_port_nr(self):
        src_host = self.get_src_node().get_host()
        dst_port_nr = self.get_dst_port().get_port_nr()
        dst_host = self.get_dst_node().get_host()
        self.get_src_port().set_ip_destination(dst_host, dst_port_nr)

        if self.has_attr(ATTR_EXTERNAL_NAME, incl_dflt=False):
            ext_name = self.get_attr(ATTR_EXTERNAL_NAME)
            self._external_dst = (ext_name, dst_host, dst_port_nr)

    def get_external_dst(self):
        return self._external_dst


class Port(dfl.Port):
    pass


# class TimerPort(dfl.TimerPort, Port):
#     def deploy(self, node_inst):
#         pass


class InPort(dfl.InPort, Port):
    def __init__(self, port_node, parent_node_def, context):
        super().__init__(port_node, parent_node_def, context)
        if not parent_node_def.is_system_nodedef():
            self._ip_port_nr = context.fetch_new_port_nr()

    def get_port_nr(self):
        return self._ip_port_nr

    def set_port_nr(self, ip_port_nr):
        self._ip_port_nr = ip_port_nr

    def deploy(self, node_inst):

        msg = {
            'cfg-kind': 'in-port',
            'name': self.get_name(),
            'ip-addr': node_inst.get_host(),
            'ip-port': self._ip_port_nr
        }
        if use_csv:
            serialized_msg = '{cfg-kind},{name},{ip-addr},{ip-port}'.format_map(msg)
        else:
            serialized_msg = json.dumps(msg)
        node_inst.send_config(serialized_msg.encode(encoding='UTF-8'))

    def __str__(self):
        return '{}:{}({},{})'.format(self.get_node_def().get_name(),
                                     self.get_name(),
                                     self.get_node_def().get_host(),
                                     self._ip_port_nr)


class OutPort(dfl.OutPort, Port):
    def set_ip_destination(self, ip_host, ip_port):
        self._ip_host = ip_host
        self._ip_port_nr = ip_port

    def deploy(self, node_inst):
        print('OutPort: {!r}'.format(self.get_name()));
        msg = {
            'cfg-kind': 'out-port',
            'name': self.get_name(),
            'ip-addr': self._ip_host,
            'ip-port': self._ip_port_nr
        }
        if use_csv:
            serialized_msg = '{cfg-kind},{name},{ip-addr},{ip-port}'.format_map(msg)
        else:
            serialized_msg = json.dumps(msg)
        node_inst.send_config(serialized_msg.encode(encoding='UTF-8'))

    def __str__(self):
        return '{}:{}({},{})'.format(self.get_node_def().get_name(),
                                     self.get_name(),
                                     self._ip_host,
                                     self._ip_port_nr)


class NodeInstance(dfl.NodeInstance):
    def __init__(self, name, parent, node_def, parameters, context):
        super().__init__(name, parent, node_def, parameters, context)
        self._host = None
        self._cfg_port = None

    def get_host(self):
        if self._host == None:
            if self.is_system_node():
                return None
            self._host = self.get_parameter('deployment-host')
            if not self._host:
                fatal('Node "{}" is missing parameter "deployment-host"'
                      .format(self))
        return self._host

    def get_cfg_port(self):
        if self._cfg_port == None:
            cfg_port = self.get_parameter('deployment-cfg-port')
            if not cfg_port:
                fatal('Node "{}" is missing parameter "deployment-cfg-port"'
                      .format(self))
            if isinstance(cfg_port, str):
                cfg_port = int(cfg_port, 0)
            self._cfg_port = cfg_port
        return self._cfg_port

    def collect_atom_names(self, frame):
        node_def = self.get_nodedef()
        ####print('Collecting atoms: node_def={}'.format(node_def))
        atom_names = set(self.resolve_atom_names(frame))
        ####print('  atom_names={}'.format(atom_names))
        if not node_def.is_intrinsic():
            node_frame = frame.get_child_by_node(self, create=True)
            for n in node_def.get_subnodes(include_system=False):
                ####print('  subnode={} >>>'.format(n))
                atom_names.update(n.collect_atom_names(node_frame))
                ####print('  <<< atom_names={}'.format(atom_names))
        return atom_names

    def push_atoms(self, frame):
        node_def = self.get_nodedef()
        ctxt = self.get_context()
        atom_names = self.collect_atom_names(frame)
        atoms = [ { 'name': name, 'id-nr': ctxt.get_atom_id_nr(name) }
                  for name in atom_names ]

        if node_def.has_role('dynamic-atom-user'):
            # Should not send the atoms just yet, because all atoms will
            # be sent to this node in next step. But the collection of
            # atoms above still needs to be done.
            return

        if use_csv:
            msg = ['atoms'] + ['{name},{id-nr}'.format_map(a) for a in atoms]
            serialized_msg = ','.join(msg)
        else:
            msg = {
                'cfg-kind': 'atoms',
                'atoms': atoms
            }
            serialized_msg = json.dumps(msg)
        self.send_config(serialized_msg.encode(encoding='UTF-8'))

    def push_all_atoms(self):
        node_def = self.get_nodedef()
        if not node_def.has_role('dynamic-atom-user'):
            return

        ctxt = self.get_context()
        atoms = [ { 'name': name, 'id-nr': id_nr }
                  for name, id_nr in ctxt.get_atoms().items() ]
        if use_csv:
            msg = ['atoms'] + ['{name},{id-nr}'.format_map(a) for a in atoms]
            serialized_msg = ','.join(msg)
        else:
            msg = {
                'cfg-kind': 'atoms',
                'atoms': atoms
            }
            serialized_msg = json.dumps(msg)
        self.send_config(serialized_msg.encode(encoding='UTF-8'))

    def configure_subnodes(self):
        ctxt = self.get_context()
        print('Port base: {}'.format(ctxt.get_port_base()))
        guard_period = ctxt.get_guard_period()
        node_def = self.get_nodedef()
        top_frame = self.get_top_frame()
        subnodes = node_def.get_subnodes(include_system=False)
        for e in node_def.get_edges():
            e.resolve_port_nr()

        print('Nodes:')
        for n in subnodes:
            print('  {}'.format(n))
        print('Edges:')
        for e in node_def.get_edges():
            print('  {}'.format(e))

        for n in subnodes:
            n.push_atoms(top_frame)
        for n in subnodes:
            n.push_all_atoms()
        for n in subnodes:
            n.deploy_inports()
        if guard_period > 0:
            time.sleep(guard_period)
        for n in subnodes:
            n.deploy_outports()

        ns = ctxt.get_ns()
        for e in node_def.get_edges():
            ext_dst = e.get_external_dst()
            if ext_dst:
                ext_name, dst_host, dst_port = ext_dst
                ns.set(ext_name, (dst_host, dst_port))

    def deploy_inports(self):
        for p in self.get_inports():
            p.deploy(self)

    def deploy_outports(self):
        for p in self.get_outports():
            p.deploy(self)

    def send_config(self, msg):
        print(msg)
        self.get_context().sendto(self.get_host(), self.get_cfg_port(), msg)


class NodeDef(dfl.NodeDef):
    def __init__(self, name, context, spec=None):
        super().__init__(name, context, spec=spec)


class NameService(object):
    def __init__(self, host, port):
        self._host = host
        self._port = port

    def set(self, name, value):
        msg = {
            'command': 'set',
            'name': name,
            'value': value
        }
        resp = self.send_to_ns(msg)
        status = resp['status']
        if status != 0:
            fatal('Cannot set key/value {!r}/{!r} in name service {!r}:{}, '
                  'status={}'.format(name, value, self._host, self._port,
                                     status))

    def get(self, name):
        msg = {
            'command': 'get',
            'name': name
        }
        resp = self.send_to_ns(msg)
        status = resp['status']
        if status != 0:
            fatal('Cannot get key {!r} from name service {!r}:{}, status={}'
                  .format(name, self._host, self._port, status))
        return resp['value']

    def send_to_ns(self, msg):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cfg_sock:
            cfg_sock.connect((self._host, self._port))
            cfg_sock.sendall(json.dumps(msg).encode(encoding='UTF-8'))
            data = cfg_sock.recv(1024)
            if not data:
                return { 'status': 99 }
            return json.loads(data.decode(encoding='UTF-8'))


class Context(dfl.Context):
    def __init__(self, port_base, ns_host, ns_port, guard_period,
                 search_paths=None):
        self._port_base = port_base
        self._next_port = port_base
        self._sock = None
        self._name_service = NameService(ns_host, ns_port)
        self._guard_period = guard_period
        self._atoms = {}
        super().__init__(search_paths=search_paths)

    def get_ns(self):
        return self._name_service

    def get_port_base(self):
        return self._port_base

    def get_guard_period(self):
        return self._guard_period

    def fetch_new_port_nr(self):
        p = self._next_port
        self._next_port += 1
        return p

    def sendto(self, host, port, msg):
        if not self._sock:
            self._sock = socket.socket(socket.AF_INET,
                                       socket.SOCK_DGRAM)
        self._sock.sendto(msg, (host, port))

    def cleanup(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    def get_atoms(self):
        return self._atoms

    def get_atom_id_nr(self, name):
        if name in self._atoms:
            id_nr = self._atoms[name]
        else:
            id_nr = len(self._atoms) + 1
            self._atoms[name] = id_nr
        return id_nr


def main():
    argparser = argparse.ArgumentParser(description='Configures nodes into a flow graph.')
    argparser.add_argument('--flow', '-F', required=True,
                           help='name of the flow definition')
    argparser.add_argument('--search-path', '-I', action='append',
                           help='adds path to search for flow def files')
    argparser.add_argument('--port-base', '-B', type=int, default=1234,
                           help='start number when generating port numbers')
    argparser.add_argument('--ns-address', '-A', default='localhost',
                           help='host that the name service is running on')
    argparser.add_argument('--ns-port', '-P', type=int, default=0xdf1b,
                           help='port that the name service is listening on')
    argparser.add_argument('--guard-period', '-G', type=float, default=0.5,
                           help='seconds to wait after config of inports before config of outports')
    argparser.add_argument('--csv', action='store_true',
                           help='use CSV format instead of JSON for info to target nodes')
    argparser.add_argument('--debug', action='store_true',
                           help='turn on debug printouts')
    args = argparser.parse_args()

    global debug_printing
    debug_printing = args.debug
    dfl.debug_printing = debug_printing

    global use_csv
    use_csv = args.csv

    ns_port = args.ns_port
    port_base = args.port_base
    if PORT_OFFSET_VAR in os.environ:
        port_offset = int(os.environ[PORT_OFFSET_VAR], 0)
        ns_port += port_offset
        port_base += port_offset

    ctxt = Context(port_base, args.ns_address, ns_port, args.guard_period,
                   search_paths=args.search_path)
    graph = ctxt.load_node(args.flow)
    graph.configure_subnodes()
    ctxt.cleanup()

if __name__ == '__main__':
    main()
