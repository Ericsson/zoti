#!/usr/bin/env python3
# Copyright (C) Ericsson AB, 2020
#
# The document(s) may be used, copied or otherwise distributed only with
# the written permission from Ericsson AB or in accordance with the
# terms and conditions stipulated in the agreement/contract under which
# the document(s) have been supplied.
#

import sys
import os
import stat
import argparse
import pathlib
import socket
import socketserver
import json
import subprocess
import hashlib


DFLT_BINS_STORAGE = 'bins_storage'

XTERMS_MAX_HEIGHT = 3
XTERMS_X_OFFSET = 0
XTERMS_Y_OFFSET = 25
XTERMS_FULL_WIDTH = 375
XTERMS_FULL_HEIGHT = 167

PORT_OFFSET_VAR = 'DFL_PORT_OFFSET'


debug_printing = False

def debug(msg):
    if debug_printing:
        print(msg)

def fatal(msg):
    sys.stderr.write('Error: {}\n'.format(msg))
    sys.exit(1)


class Request(object):
    def __init__(self, server, data, stream):
        self._server = server
        self._request_data = data
        self._stream = stream
        self._resp = { 'status': 0 }

    def execute(self):
        pass

    def get_response(self):
        return self._resp


class InfoRequest(Request):
    def execute(self):
        res = subprocess.run(['uname', '-m'], stdout=subprocess.PIPE)
        arch = res.stdout.decode().strip()
        self._resp = {
            'status': 0,
            'machine-arch': arch,
            'running-procs': list(self._server.get_proc_info_ids())
        }


class LoadRequest(Request):
    def execute(self):
        name = self._request_data['name']
        bin_size = self._request_data['size']
        sha256 = self._request_data['sha256']

        # Acknowledge that the command has been received and the binary
        # data may be sent.
        resp = { 'status': 0, 'continue': True }
        data = json.dumps(resp).encode(encoding='UTF-8')
        self._stream.sendall(data)

        print('vv name: {!r}, size: {!r}'.format(name, bin_size))

        bins_storage_dir = self._server.get_bins_storage_dir()
        bins_storage_dir.mkdir(parents=True, exist_ok=True)

        status = 0
        hash = hashlib.sha256()
        fpath = bins_storage_dir / name
        with fpath.open('wb') as f:
            while bin_size > 0:
                bin_data = self._stream.recv(4096)
                if len(bin_data) == 0:
                    status = 1
                    break
                hash.update(bin_data)
                f.write(bin_data)
                bin_size -= len(bin_data)

        if hash.hexdigest() == sha256:
            fstat = fpath.stat()
            fpath.chmod((fstat.st_mode | stat.S_IXUSR) &
                        ~(stat.S_IRWXG | stat.S_IRWXO))
            self._server.store_bin_info(name, (name, fpath, sha256))
        else:
            status = 2

        self._resp = {
            'status': status,
            'continue': False
        }


class StartRequest(Request):
    def execute(self):
        ident = self._request_data['proc-id']
        bin_name = self._request_data['name']
        port = self._request_data['cfg-port']

        _, binfile_path, sha256 = self._server.get_bin_info(bin_name)
        with binfile_path.open('rb') as f:
            binary = f.read()
        hash = hashlib.sha256()
        hash.update(binary)

        status = 0
        if hash.hexdigest() == sha256:
            cmd = ['sh', '-c', '{!s} --dfl-cfg-port={}; echo "Exited: $?"; read a'.format(binfile_path, port)]
            #cmd = [str(binfile_path), '--dfl-cfg-port={}'.format(port)]

            in_window = self._request_data.get('in-window', False)
            geom = None
            if in_window == 'all':
                geom = '60x10'
            elif in_window > 0:
                logical_pos = in_window - 1
                x = (logical_pos // XTERMS_MAX_HEIGHT) * XTERMS_FULL_WIDTH \
                    + XTERMS_X_OFFSET
                y = (logical_pos % XTERMS_MAX_HEIGHT) * XTERMS_FULL_HEIGHT \
                    + XTERMS_Y_OFFSET
                if in_window == 7: #Hack: to get larger window for Sink
                    geom_size = '60x23'
                else:
                    geom_size = '60x10'
                geom = '{}+{}+{}'.format(geom_size, x, y)
            if geom:
                cmd = ['xterm', '-title', bin_name, '-geometry', geom, '-e'] + cmd

            print('>> cmd: {!r}'.format(cmd))
            proc = subprocess.Popen(cmd)
            self._server.store_proc_info(ident, proc)
        else:
            status = 2

        self._resp = {
            'status': status
        }


class StopRequest(Request):
    def execute(self):
        ident = self._request_data['proc-id']
        proc = self._server.get_proc_info(ident)
        print('XX proc: {!r}'.format(proc))
        proc.terminate()
        try:
            proc.wait(timeout=1)
        except TimeoutExpired:
            proc.kill()

        self._server.remove_proc_info(ident)

        self._resp = {
            'status': 0
        }


commands = {
    'info':  InfoRequest,
    'load':  LoadRequest,
    'start': StartRequest,
    'stop':  StopRequest
}


class RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(1024)
        req = json.loads(data.decode(encoding='UTF-8'))
        print('req: {!r}'.format(req))

        req_cls = commands[req['command']]
        req_obj = req_cls(self.server, req, self.request)

        req_obj.execute()

        resp = req_obj.get_response()
        data = json.dumps(resp).encode(encoding='UTF-8')
        self.request.sendall(data)


class AgentServer(socketserver.TCPServer):
    def __init__(self, server_address, req_handler_cls, bins_storage_dir):
        super().__init__(server_address, req_handler_cls)
        self._proc_info = {}
        self._bin_info = {}
        self._bins_storage_dir = pathlib.Path(bins_storage_dir)

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

    def store_proc_info(self, ident, proc_info):
        self._proc_info[ident] = proc_info

    def get_proc_info(self, ident):
        print('ident={!r}'.format(ident))
        print('proc_info={!r}'.format(self._proc_info))
        return self._proc_info[ident]

    def get_proc_info_ids(self):
        return self._proc_info.keys()

    def remove_proc_info(self, ident):
        del self._proc_info[ident]

    def store_bin_info(self, name, info):
        self._bin_info[name] = info

    def get_bin_info(self, name):
        return self._bin_info[name]

    def get_bins_storage_dir(self):
        return self._bins_storage_dir


def main():
    argparser = argparse.ArgumentParser(description='Life-cycle management of flow binaries.')
    argparser.add_argument('--address', '-A', default='',
                           help='address/host for ifc to listen on')
    argparser.add_argument('--port', '-P', type=int, default=0xdf1a,
                           help='port to listen for management commands on')
    argparser.add_argument('--bins-storage', default=DFLT_BINS_STORAGE,
                           help='directory for storing downloaded binaries')
    argparser.add_argument('--debug', action='store_true',
                           help='turn on debug printouts')
    args = argparser.parse_args()

    global debug_printing
    debug_printing = args.debug

    port = args.port
    if PORT_OFFSET_VAR in os.environ:
        port += int(os.environ[PORT_OFFSET_VAR], 0)

    server = AgentServer((args.address, port), RequestHandler,
                         args.bins_storage)
    server.serve_forever()

if __name__ == '__main__':
    main()
