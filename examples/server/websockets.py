#!/usr/bin/env python2

import sys
sys.path.insert(0, '.')

from server import HTTPServer
from resource import BaseResource as Resource
from circuits import Debugger, handler
from circuits.net.events import write
from circuits.http.server.resource import method
from circuits.http.server.connection import Websocket

from httoop import BAD_REQUEST


class Root(Resource):

	channel = '/'

	def init(self, **kwargs):
		self += Websocket(channel=self.channel)

	@handler('read')
	def _on_read(self, socket, data):
		self.fire(write(b'Thank you for %d bytes!' % (len(data),)))

	@method
	def GET(self, client):
		response = BAD_REQUEST('Upgrade to websocket required!')
		response.body = open('websocket.html').read()
		client.response.headers['Content-Type'] = 'text/html'
		raise response


if __name__ == '__main__':
	server = HTTPServer()
	server.localhost += Root()
	server += Debugger(events=True)
	server.run()

