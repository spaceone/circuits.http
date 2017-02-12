#!/usr/bin/env python2
"""
curl -i http://localhost:8090/graph
"""
import sys
sys.path.insert(0, '.')
from datetime import datetime

from server import HTTPServer as _HTTPServer
from circuits import handler, BaseComponent, Debugger
from circuits.tools import graph
from circuits.http.server.resource import Resource, method, Method, Domain


class BaseResource(Resource):

	@method
	def GET(self, client):
		return graph(self.root) + '\n'
	GET.codec('text/plain')

	def etag(self, client):
		return bytes(hash(self))

	def last_modified(self, client):
		return datetime.now()

	def content_language(self, client):
		return 'en-us'


class HTTPServer(_HTTPServer):

	def __init__(self):
		super(HTTPServer, self).__init__()
		self.localhost += BaseResource(channel='/:path')


if __name__ == '__main__':
	server = HTTPServer()
	server += Debugger(events=True)
	server.run()
