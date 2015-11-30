#!/usr/bin/env python2
"""
curl -i https://localhost:8443/ --cacert ~/git/circuits.http/examples/server/ssl/ca-chain.pem -k
"""

import sys
sys.path.insert(0, '.')

from server import HTTPServer
from resource import BaseResource as Resource
from circuits import Debugger
from circuits.http.server.resource import method
from circuits.net.sockets import TCPServer


sslsocket = lambda channel: TCPServer(('', 8443), secure=True, certfile='./ssl/server-cert.pem', keyfile='./ssl/server-key.pem', channel=channel)


class Secured(Resource):

	channel = '/'

	@method
	def GET(self, client):
		return {"message": "This connection uses TLS: %s" % (client.server.secure,)}
	GET.codec('application/json')


if __name__ == '__main__':
	server = HTTPServer()
	server += sslsocket(server.channel)
	server.localhost += Secured()
	server += Debugger(events=True)
	server.run()
