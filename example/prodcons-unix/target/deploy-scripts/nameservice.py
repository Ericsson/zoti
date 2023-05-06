#!/usr/bin/env python3
# Copyright (C) Ericsson AB, 2020
#
# The document(s) may be used, copied or otherwise distributed only with
# the written permission from Ericsson AB or in accordance with the
# terms and conditions stipulated in the agreement/contract under which
# the document(s) have been supplied.
#

import os
import sys
import argparse
import socket
import socketserver
import json


PORT_OFFSET_VAR = 'DFL_PORT_OFFSET'


debug_printing = False

def debug(msg):
    if debug_printing:
        print(msg)

def fatal(msg):
    sys.stderr.write('Error: {}\n'.format(msg))
    sys.exit(1)


register = {}


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


class SetValueRequest(Request):
    def execute(self):
        name = self._request_data['name']
        value = self._request_data['value']
        debug('Set {!r}={!r}'.format(name, value))

        register[name] = value

        self._resp = {
            'status': 0
        }


class GetValueRequest(Request):
    def execute(self):
        name = self._request_data['name']

        if name in register:
            debug('Get {!r} -> {!r}'.format(name, register[name]))
            self._resp = {
                'status': 0,
                'value': register[name]
            }
        else:
            debug('Get {!r} (not defined)'.format(name))
            self._resp = {
                'status': 1
            }


commands = {
    'set':  SetValueRequest,
    'get':  GetValueRequest
}


class RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(1024)
        req = json.loads(data.decode(encoding='UTF-8'))

        req_cls = commands[req['command']]
        req_obj = req_cls(self.server, req, self.request)

        req_obj.execute()

        resp = req_obj.get_response()
        data = json.dumps(resp).encode(encoding='UTF-8')
        self.request.sendall(data)


class NameServer(socketserver.TCPServer):
    def __init__(self, server_address, req_handler_cls):
        super().__init__(server_address, req_handler_cls)

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()


def main():
    argparser = argparse.ArgumentParser(description='Simple name service.')
    argparser.add_argument('--address', '-A', default='',
                           help='address/host for ifc to listen on')
    argparser.add_argument('--port', '-P', type=int, default=0xdf1b,
                           help='port to listen for requests on')
    argparser.add_argument('--debug', action='store_true',
                           help='turn on debug printouts')
    args = argparser.parse_args()

    global debug_printing
    debug_printing = args.debug

    port = args.port
    if PORT_OFFSET_VAR in os.environ:
        port += int(os.environ[PORT_OFFSET_VAR], 0)
    debug('port={}'.format(port))

    server = NameServer((args.address, port), RequestHandler)
    server.serve_forever()

if __name__ == '__main__':
    main()
