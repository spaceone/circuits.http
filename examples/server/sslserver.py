#!/usr/bin/env python2

import sys
sys.path.insert(0, '.')

from server import HTTPServer
from resource import BaseResource as Resource
from circuits import Debugger
from circuits.http.server.resource import method
from circuits.net.sockets import TCPServer


sslsocket = TCPServer(('', 8443), secure=True, certfile='./ssl/cert.pem')


class Secured(Resource):

	channel = '/'

	@method
	def GET(self, client):
		return {"message": "Using SSL: %s" % (client.server.secure,)}
	GET.codec('application/json')


if __name__ == '__main__':
	server = HTTPServer()
	server += sslsocket
	server.localhost += Secured()
	server += Debugger(events=True)
	server.run()

