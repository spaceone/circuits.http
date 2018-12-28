# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import traceback

from circuits import BaseComponent, handler, Worker, task
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
	def main(cls, args):
		return super(WSGIServer, cls).main(['-w', '-n'] + list(args))


class Application(BaseComponent):

	def __init__(self, ServerClass, *args):
		server = ServerClass.main(args)
		super(Application, self).__init__(channel=server.channel)
		server.register(self)

	def init(self, *args, **kwargs):
		self.requests = []
		self.responses = []

	def __call__(self, environ, start_response, exc_info=None):
		try:
			client = WSGIClient(environ=environ, use_path_info=True)

			self.secure = client.request.uri.scheme == 'https'
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

	@handler('started', priority=-1)
	def on_started(self, *args, **kwargs):
		for client in self.requests:
			scheme = client.request.uri.scheme
			client.request.uri.scheme = None
			yield  # self.wait('routes.create')  # handle all other started events, which are registering the routes
			self.fire(read(client.socket, (str(client.request) + str(client.request.headers) + str(client.request.body))), self.channel)
			client.request.uri.scheme = scheme

	@handler("response.body", priority=1.1)
	def on_response(self, event, client):
		self._running = False
		self.responses.append(client)
		event.stop()


class Gateway(BaseComponent):

	def __init__(self, application, *args, **kwargs):
		self.application = application
		self.multiprocess = kwargs.get('multiprocess', False)
		self.multithread = kwargs.get('multithread', False)
		self.worker = kwargs.get('worker', None)
		super(Gateway, self).__init__(*args, **kwargs)
		if self.multithread or self.multiprocess:
			Worker(self.multiprocess, self.worker, channel=self.channel).register(self)

	@httphandler('request', priority=1.1)
	def _on_request_stop(self, event, client):
		event.stop()  # Workaround for circuits error not calling coroutines

	@httphandler('request', priority=1.2)
	def _on_request(self, event, client):
		event.stop()
		environ = {
			'wsgi.errors': StringIO(),
			'wsgi.run_once': False,
			'wsgi.multithread': self.multithread,
			'wsgi.multiprocess': self.multiprocess,
			'PATH_INFO': client.path_segments.get('path_info'),
		}
		wsgi = WSGIClient(client.request, None, client.socket, client.server, environ)
		if self.multiprocess or self.multithread:
			yield self.call(task(wsgi, self.application))
		else:
			wsgi(self.application)
		if wsgi.exc_info:
			try:
				reraise(wsgi.exc_info[0], wsgi.exc_info[1], wsgi.exc_info[2])
			finally:
				wsgi.exc_info = None
		client.response = wsgi.response
		self.fire(RE(client), client.server.channel)
