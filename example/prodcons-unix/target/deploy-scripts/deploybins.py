#!/usr/bin/env python3
# Copyright (C) Ericsson AB, 2019
#
# The document(s) may be used, copied or otherwise distributed only with
# the written permission from Ericsson AB or in accordance with the
# terms and conditions stipulated in the agreement/contract under which
# the document(s) have been supplied.
#

import sys
import os
import os.path
import time
import argparse
import pathlib
import re
import shutil
import importlib
import itertools
import socket
import json
import hashlib

import dfl


PORT_OFFSET_VAR = 'DFL_PORT_OFFSET'


debug_printing = False

def debug(msg):
    if debug_printing:
        print(msg)

def error(msg):
    sys.stderr.write('Error: {}\n'.format(msg))

def fatal(msg):
    error(msg)
    sys.exit(1)


class NodeInstance(dfl.NodeInstance):
    def __init__(self, name, parent, node_def, parameters, context):
        super().__init__(name, parent, node_def, parameters, context)
        self._bin_name = None
        self._host = None
        self._cfg_port = None
        self._in_window = None

    def get_binfile_name(self):
        if self._bin_name == None:
            self._bin_name = self.get_parameter('deployment-bin-file')
            if self._bin_name is None:
                fatal('Node "{}" is missing parameter "deployment-bin-file"'
                      .format(self))
        return self._bin_name

    def get_host(self):
        if self._host == None:
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

    def get_in_window(self):
        if self._in_window == None:
            self._in_window = self.get_parameter('deployment-in-window',
                                                 dflt=False)
        return self._in_window

    def download_to_agent(self):
        binfile_name = self.get_binfile_name()
        if binfile_name == '':
            # No binfile, nothing to download.
            return

        print('Downloding node binary for {!r}'.format(self.get_name()));

        msg = {
            'command': 'info'
        }
        resp = self.send_to_agent(msg)
        status = resp['status']
        if status != 0:
            fatal('Cannot retrieve info from agent on {!r}, status={}'
                  .format(self.get_host(), status))

        march = resp['machine-arch']
        print('  Need machine arch {!r}'.format(march))

        binfile_relpath = os.path.join(march, binfile_name)
        binfile_path = self.get_context().find_binfile(binfile_relpath)
        if not binfile_path:
            fatal('Cannot find file {}'.format(binfile_name))
        with binfile_path.open('rb') as f:
            binary = f.read()
        hash = hashlib.sha256()
        hash.update(binary)

        msg = {
            'command': 'load',
            'name': self.get_name(),
            'size': len(binary),
            'sha256': hash.hexdigest()
        }
        resp = self.send_to_agent(msg, binary)
        if resp['status'] == 0:
            print('  Success')
        else:
            fatal('Download failed, status={!r}'.format(resp['status']))

    def start_node(self, window_all):
        binfile_name = self.get_binfile_name()
        if binfile_name == '':
            # No binfile, nothing to start.
            return

        print('Starting node {!r}'.format(self.get_name()));

        cfg_port = self.get_cfg_port()
        in_window = 'all' if window_all else self.get_in_window()
        msg = {
            'command': 'start',
            'proc-id': self.get_name(),
            'name':  self.get_name(),
            'cfg-port': cfg_port,
            'in-window': in_window
        }
        resp = self.send_to_agent(msg)
        if resp['status'] == 0:
            print('  Success')
        else:
            fatal('Start failed, status={!r}'.format(resp['status']))

    def stop_node(self):
        binfile_name = self.get_binfile_name()
        if binfile_name == '':
            # No binfile, nothing to stop.
            return

        print('Stopping node {!r}'.format(self.get_name()));

        msg = {
            'command': 'stop',
            'proc-id': self.get_name()
        }
        resp = self.send_to_agent(msg)
        if resp['status'] == 0:
            print('  Success')
        else:
            print('  Stop failed, status={!r}'.format(resp['status']))

    def send_to_agent(self, msg, binary=None):
        host = self.get_host()
        port = self.get_context().get_agent_port()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cfg_sock:
            cfg_sock.connect((host, port))
            cfg_sock.sendall(json.dumps(msg).encode(encoding='UTF-8'))
            if binary:
                data = cfg_sock.recv(1024)
                resp = json.loads(data.decode())
                status = resp['status']
                if status != 0:
                    error('Command failed, status={!r}'.format(status))
                    return resp
                if not resp.get('continue'):
                    error('Missing "continue" response for binary transfer.')
                    return { 'status': 98 }
                cfg_sock.sendall(binary)
            data = cfg_sock.recv(1024)
            if not data:
                return { 'status': 99 }
            return json.loads(data.decode(encoding='UTF-8'))


class NodeDef(dfl.NodeDef):
    def __init__(self, name, context, spec=None):
        super().__init__(name, context, spec=spec)

    def download_node_bins(self):
        subnodes = self.get_subnodes(include_system=False)

        print('Nodes:')
        for n in subnodes:
            print('  {}'.format(n.get_name()))

        for n in subnodes:
            n.download_to_agent()

    def start_nodes(self, window_all):
        subnodes = self.get_subnodes(include_system=False)

        print('Nodes:')
        for n in subnodes:
            print('  {}'.format(n.get_name()))

        for n in subnodes:
            n.start_node(window_all)

    def stop_nodes(self):
        subnodes = self.get_subnodes(include_system=False)

        print('Nodes:')
        for n in subnodes:
            print('  {}'.format(n.get_name()))

        for n in subnodes:
            n.stop_node()


class Context(dfl.Context):
    def __init__(self, search_paths=None, bin_paths=None, agent_port=0xdf1a):
        super().__init__(search_paths=search_paths)
        self._agent_port = agent_port
        self._bin_repo = dfl.FileRepo(bin_paths)

    def get_agent_port(self):
        return self._agent_port

    def find_binfile(self, fname, exts=None):
        return self._bin_repo.find_file(fname, exts)

    def cleanup(self):
        pass


def main():
    argparser = argparse.ArgumentParser(description='Configures nodes into a flow graph.')
    argparser.add_argument('--download', action='store_true',
                           help='download node binaries to agents')
    argparser.add_argument('--start', action='store_true',
                           help='start the nodes in the flow')
    argparser.add_argument('--stop', action='store_true',
                           help='stop the nodes in the flow')
    argparser.add_argument('--flow', '-F', required=True,
                           help='name of the flow definition')
    argparser.add_argument('--search-path', '-I', action='append',
                           help='adds path to search for flow def files')
    argparser.add_argument('--bin-path', '-B', action='append',
                           help='adds path to search for bin files')
    argparser.add_argument('--agent-port', '-P', type=int, default=0xdf1a,
                           help='port that the agents are listening on')
    argparser.add_argument('--window-all', action='store_true',
                           help='start all nodes in windows')
    argparser.add_argument('--debug', action='store_true',
                           help='turn on debug printouts')
    args = argparser.parse_args()

    global debug_printing
    debug_printing = args.debug
    dfl.debug_printing = debug_printing

    agent_port = args.agent_port
    if PORT_OFFSET_VAR in os.environ:
        agent_port += int(os.environ[PORT_OFFSET_VAR], 0)

    ctxt = Context(search_paths=args.search_path, bin_paths=args.bin_path,
                   agent_port=agent_port)
    graph = ctxt.load_node_def(args.flow)
    if args.download:
        graph.download_node_bins()
    elif args.start:
        graph.start_nodes(args.window_all)
    elif args.stop:
        graph.stop_nodes()
    else:
        fatal('No command given. Use --download, --start or --stop')
    ctxt.cleanup()

if __name__ == '__main__':
    main()
