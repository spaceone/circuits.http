# -*- coding: utf-8 -*-
import sys
import traceback

from circuits.core import BaseComponent, handler
from circuits.tools import tryimport
from circuits.net.events import read
from circuits.six import reraise

from circuits.http.wrapper import Client, Host
from circuits.http.utils import httphandler
from circuits.http.events import response as RE
from circuits.http.server.__main__ import HTTPServer

from httoop import Request, Response
from httoop.gateway.wsgi import WSGI
StringIO = tryimport(("cStringIO", "StringIO", "io"), "StringIO")


class WSGIClient(Client, WSGI):

	def __init__(self, request=None, response=None, socket=None, server=None, *args, **kwargs):
		Client.__init__(self, request or Request(), response or Response(), socket, server)
		WSGI.__init__(self, *args, **kwargs)

	def from_environ(self, environ):
		super(WSGIClient, self).from_environ(environ)
		self.remote = Host(self.remote_address, self.remote_port)


class WSGIServer(HTTPServer):

	@classmethod
	def main(cls, *args):
		return super(WSGIServer, cls).main(['-w', '-n'] + list(args))


class Application(BaseComponent):

	def init(self, server, *args, **kwargs):
		self.server = server
		self.requests = []
		self.responses = []

	def __call__(self, environ, start_response, exc_info=None):
		try:
			client = WSGIClient(environ=environ, use_path_info=True)
			client.from_environ(environ)

			self.secure = client.request.uri.scheme == 'https'
			self.host = Host(client.server_address, client.server_port)
			self.host = client.server_address
			self.port = client.server_port

			self.requests.append(client)
			self.run()

			for client in self.responses:
				status = str(client.response.status)
				headers = [(key.encode(), value.encode()) for key, value in client.response.headers.items()]

				start_response(status, headers, exc_info)
				return client.response.body.__iter__()
		except Exception:
			start_response('500 Internal Server Error', [('Content-Type', 'text/plain')], sys.exc_info())
			return [traceback.format_exc()]

	@handler('started')
	def on_started(self, *args, **kwargs):
		for client in self.requests:
			scheme = client.request.uri.scheme
			client.request.uri.scheme = None
			yield
			self.fire(read(client.socket, (str(client.request) + str(client.request.headers) + str(client.request.body))), self.server.channel)
			client.request.uri.scheme = scheme

	@handler("response.body", priority=1.1)
	def on_response(self, event, client):
		self._running = False
		self.responses.append(client)
		event.stop()


class Gateway(BaseComponent):
	# TODO: add possibility for a thread pool

	def init(self, application, *args, **kwargs):
		self.application = application

	@httphandler('request', priority=0.8)
	def _on_request(self, event, client):
		event.stop()

		wsgi = WSGIClient(client.request, None, client.socket, client.server, environ={})
		wsgi.errors = StringIO()

		def start_response(status, headers, exc_info=None):  # TODO: what to do with exc_info?
			wsgi.response.status.parse(status)
			wsgi.exc_info = exc_info
			for key, value in headers:
				wsgi.response.headers.append(key, value)
			return wsgi.response.body.write

		environ = wsgi._get_environ()
		if 'path_info' in client.path_segments:
			environ['PATH_INFO'] = client.path_segments['path_info']

		body = self.application(environ, start_response)

		if wsgi.exc_info:
			reraise(wsgi.exc_info[0], wsgi.exc_info[1], wsgi.exc_info[2])

		client.response = wsgi.response
		# TODO: must iterate over the first item
		if body and (not isinstance(body, (list, tuple)) or len(body) != 1 or body[0]):
			client.response.body = body

		self.fire(RE(client), client.server.channel)
