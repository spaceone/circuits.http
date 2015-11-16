#!/usr/bin/env python2

import sys
sys.path.insert(0, '.')
from ssl import CERT_OPTIONAL

from server import HTTPServer
from resource import BaseResource as Resource
from circuits import Debugger
from circuits.http.server.resource import method
from circuits.net.sockets import TCPServer


class SSLSocket(TCPServer):

	def __init__(self, channel):
		super(SSLSocket, self).__init__(
			('', 8443),
			secure=True,
			certfile="./ssl/server-cert.pem",
			keyfile="./ssl/server-key.pem",
			ca_certs=["./ssl/ca-chain.pem"],
			cert_reqs=CERT_OPTIONAL,
			channel=channel,
		)


class PeerCert(Resource):

	channel = '/'

	@method
	def GET(self, client):
		return "Here's your cert %s" % client.ssl.cert
	GET.codec('application/json')


if __name__ == '__main__':
	server = HTTPServer()
	server += SSLSocket(channel=server.channel)
	server.localhost += PeerCert()
	server += Debugger(events=True)
	server.run()

