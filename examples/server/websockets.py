#!/usr/bin/env python2
"""Websockets.

chromium http://localhost:8090/
firefox http://localhost:8090/
"""

import sys

sys.path.insert(0, '.')

from circuits import Debugger, handler
from circuits.http.server.connection import Websocket
from circuits.http.server.resource import method
from circuits.net.events import write

from resource import BaseResource as Resource
from server import HTTPServer


class Root(Resource):

	channel = '/'

	def init(self, server, **kwargs):
		server += Websocket('websocket', channel=self.channel)

	@handler('read', channel='websocket')
	def _on_read(self, socket, data):
		self.fire(write(socket, b'Thank you for %d bytes!' % (len(data),)), 'websocket')

	@method
	def GET(self, client):
		client.response.body = open('tpl/websocket.html', 'rb')
	def content_type(self, client):
		return 'text/html; charset="UTF-8"'


if __name__ == '__main__':
	server = HTTPServer()
	server.localhost += Root(server=server)
	server += Debugger(events=True)
	server.run()

