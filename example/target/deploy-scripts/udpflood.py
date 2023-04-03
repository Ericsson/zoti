#!/usr/bin/env python3
# Copyright (C) Ericsson AB, 2019
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
import json


PORT_OFFSET_VAR = 'DFL_PORT_OFFSET'

TRANSP_TYPE_UDP = 'UDP'
TRANSP_TYPE_TCP = 'TCP'
TRANSP_CNV_MAP = {
    TRANSP_TYPE_UDP: (socket.SOCK_DGRAM, False, False),
    TRANSP_TYPE_TCP: (socket.SOCK_STREAM, True, True)
}


debug_printing = False

def debug(msg):
    if debug_printing:
        print(msg)

def fatal(msg):
    sys.stderr.write('Error: {}\n'.format(msg))
    sys.exit(1)


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


def main():
    argparser = argparse.ArgumentParser(description='Continously sends UDP or TCP packets to one destination.')
    argparser.add_argument('--protocol', '-T', default="UDP",
                           help='protocol to use (UDP or TCP)')
    argparser.add_argument('--port-name', '-N',
                           help='host name or IP address to send to')
    argparser.add_argument('--host', '-H',
                           help='host name or IP address to send to')
    argparser.add_argument('--port', '-p',
                           help='port to send to')
    argparser.add_argument('--count', '-c', type=int, default=10,
                           help='number of packets to send')
    argparser.add_argument('--pkt-size', '-s', type=int, default=10,
                           help='size of each packet to send')
    argparser.add_argument('--ns-address', '-A', default='localhost',
                           help='host that the name service is running on')
    argparser.add_argument('--ns-port', '-P', type=int, default=0xdf1b,
                           help='port that the name service is listening on')
    argparser.add_argument('--debug', action='store_true',
                           help='turn on debug printouts')
    args = argparser.parse_args()

    global debug_printing
    debug_printing = args.debug

    if not args.port_name and not (args.host and args.port):
        fatal('Either --port-name or --host and --port must be specified')

    if args.protocol not in TRANSP_CNV_MAP:
        fatal('Invalid arg to --protocol, expected UDP or TCP')

    if args.port_name:
        ns_port = args.ns_port
        if PORT_OFFSET_VAR in os.environ:
            ns_port += int(os.environ[PORT_OFFSET_VAR], 0)
        debug('ns_port={}'.format(ns_port))
        ns = NameService(args.ns_address, ns_port)
        host, port = ns.get(args.port_name)
        print(host, port)
    else:
        host = args.host
        port = args.port

    sock_type, incl_size, sendall = TRANSP_CNV_MAP[args.protocol]
    sock = socket.socket(socket.AF_INET, sock_type)
    sock.connect((host, int(port)))
    data = bytes(os.urandom(args.pkt_size))
    print('len(data): {}'.format(len(data)))
    if incl_size:
        data = args.pkt_size.to_bytes(4, byteorder='big') + data
        print('len(size + data): {}'.format(len(data)))
    for i in range(args.count):
        if sendall:
            sock.sendall(data)
        else:
            sock.send(data)

if __name__ == '__main__':
    main()
