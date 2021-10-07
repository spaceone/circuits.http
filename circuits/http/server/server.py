# -*- coding: utf-8 -*-
"""HTTP server"""

from __future__ import absolute_import, print_function

import sys
from ssl import SSLError
from time import time
from traceback import format_exception_only, format_tb

from httoop import INTERNAL_SERVER_ERROR, Request, Response, StatusException
from httoop.semantic.response import ComposedResponse

from circuits import BaseComponent, Event, handler, reprhandler
from circuits.http.events import (
	HTTPError, request as RequestEvent, response as ResponseEvent, routing as RoutingEvent,
)
from circuits.http.server._state import State
from circuits.http.wrapper import Client, Server
from circuits.net.events import close, read, write
from circuits.net.utils import is_ssl_handshake

_ResponseStart = type('response.start', (Event,), {})
_ResponseBody = type('response.body', (Event,), {})
_ResponseComplete = type('response.complete', (Event,), {})


class HTTP(BaseComponent):
	"""HTTP Server Protocol Component

		Parse incoming HTTP messages and send a response message.
	"""

	channel = 'http'

	connection_idle_timeout = 30.0

	def __init__(self, channel=channel):
		super(HTTP, self).__init__(channel=channel)
		self._buffers = {}

	@handler("read")
	def _on_read(self, event, socket, data):
		"""parse data and fire request event"""

		server = Server(event.value.manager)

		if socket not in self._buffers:
			self._buffers[socket] = State(self, socket, server)
			if not server.secure and is_ssl_handshake(data):
				if self.ssl_through_http(socket) is NotImplemented:
					return

		if self._buffers[socket].tunnel:
			return  # TODO: find a circuits way for this

		http = self._buffers[socket].parser

		try:
			requests = tuple(http.parse(data))
		except StatusException as httperror:
			client = Client(http.request, http.response, socket, server)
			self._add_client(client)
			self.fire(HTTPError(client, httperror))
			# TODO: wait for HTTPError event to be processed and close the connection
		except BaseException:
			client = Client(Request(), Response(), socket, server)
			self._add_client(client)
			self.fire(self.default_internal_server_error(client, sys.exc_info()))
			raise
		else:
			for client in requests:
				self._add_client(client)
				client.events.routing = self.fire(RoutingEvent(client)).event  # TODO: fire routing event in on_headers_complete and wait for sending the request event until the request is parsed completely

	def _add_client(self, client):
		self._buffers[client.socket].requests.append(client)

	def on_headers_complete(self, client):
		pass

	@handler('read', 'connect', priority=-0.1)
	def _timeout(self, *args):
		self.fire(Event.create('timeout.check', args[0]))

	@handler('timeout.check')
	def _check_timeout(self, socket):
		try:
			from circuits import sleep
		except ImportError:
			return  # wrong circuits version
		try:
			state = self._buffers[socket]
		except KeyError:
			# FIXME: does not exists yet on "connect"
			return  # disconnected

		if state.tunnel:
			return
		timeout = state.timeout
		if timeout is not None:
			timeout.abort = True
			timeout.expiry = time()

		timeout = sleep(self.connection_idle_timeout)
		timeout.abort = False
		state.timeout = timeout

		yield timeout

		if timeout.abort or state.tunnel:
			return
		if all(client.done for client in state.requests):
			self.fire(close(socket))
		# else:
		# TODO: implement close after last response

	@handler("response")
	def _on_response(self, client):
		"""Send respond message to client's socket"""

		socket = client.socket

		try:
			state = self._buffers[socket]
		except KeyError:  # client disconnected before receiving answer
			self._premature_client_disconnect(client)
			return

		if client in state.responses:
			raise RuntimeError('Got multiple response events for client: %r' % (client,))

		state.responses.add(client)
		pipeline = state.requests
		if not pipeline or pipeline[0] is not client:
			return  # a previous request is unfinished

		self.fire(_ResponseStart(client))

	@handler('response.start')
	def _on_response_start(self, client):

		request, response = client
		socket = client.socket

		try:
			state = self._buffers[socket]
		except KeyError:  # client disconnected before receiving answer
			self._premature_client_disconnect(client)
			return

		state.response_started.add(client)
		if client.response.status == 101 or client.request.method == u'CONNECT' and client.response.status.successful:
			state.tunnel = True

		# prepare for sending
		composed = ComposedResponse(response, request)
		composed.prepare()
		state.composed[client] = composed

		# send HTTP response status line and headers
		bresponse = bytes(response)
		bheaders = bytes(response.headers)

		self.fire(write(socket, b'%s%s' % (bresponse, bheaders)))
		self.fire(_ResponseBody(client))

	@handler("response.body")
	def _on_response_body(self, client):
		"""stream the response output"""

		response = client.response
		socket = client.socket

		try:
			data = next(response.body)
		except StopIteration:
			response.body.close()
			# if response.close:  # conflicts with pipelining?
			# 	self.fire(close(socket))
			client.done = True
			self.fire(_ResponseComplete(client))
		else:
			self.fire(write(socket, data))
			self.fire(_ResponseBody(client))

	@handler('response.complete')
	def _on_response_complete(self, client):
		socket = client.socket

		try:
			state = self._buffers[socket]
		except KeyError:  # client disconnected
			self._premature_client_disconnect(client)
			return
		pipeline = state.requests
		assert pipeline and pipeline[0] is client
		pipeline.pop(0)

		try:
			client_ = pipeline[0]
		except IndexError:  # no further request
			if state.composed[client].close:  # FIXME: composed
				self.fire(close(socket))
		else:
			if client_ in state.responses and client_ not in state.response_started:
				self.fire(_ResponseStart(client_))

	@handler('httperror', priority=1.1)
	def _on_handle_httperror(self, event, client, httperror):
		event.ignore = False
		try:
			state = self._buffers[client.socket]
		except KeyError:
			self._premature_client_disconnect(client)
			event.ignore = True
			event.stop()
			return

		if client in state.responses:
			event.ignore = True
			event.stop()
			raise RuntimeError('Got httperror event after response event. Client: %r, HTTPError: %r. Ignoring it.' % (client, httperror))

	@handler('httperror', priority=0.1)
	def _on_httperror(self, event, client, httperror):
		event.stop()
		# TODO: move into httoop?
		# set the corresponding HTTP status
		client.response.status = httperror.status

		# set HTTP headers
		client.response.headers.update(httperror.headers)

		# set HTTP Body
		client.response.body = httperror.body

		# fire httperror_XXX event
		# channels = set([c.channel for c in (self, client.server, client.domain, client.resource) if c is not None])
		event = Event.create('httperror_%d' % (httperror.status,))
		self.fire(event, *event.channels)

	@handler("httperror_success")
	def _on_httperror_success(self, evt, httperror):
		"""default HTTP error handler"""
		if evt.ignore:
			return
		client = evt.args[0]
		client.response.body.encode()
		self.fire(ResponseEvent(client))

	@handler("request_failure", channel='*')
	def _on_request_failure(self, evt, error):
		"""Handler for exceptions occuring in the request or response event handler"""
		client = evt.args[0]

		# if client.redirected:
		# 	return
		# if isinstance(evalue, InternalRedirect):
		# 	client.request.uri = evalue.uri
		# 	client.redirected = True
		# 	self.fire(Request(client))
		# 	return

		# Ignore filtered requests already handled
		if client.handled:
			return

		# recursion impossible :)
		client.handled = True

		self._handle_exception(client, error)

	@handler("response_failure")
	def _on_response_failure(self, evt, error):
		client = evt.args[0]

		# Ignore failed "response" handlers (e.g. Loggers or Tools)
		if client.done:
			return

		# Ignore disconnected clients
		if client.socket not in self._buffers:
			client.response.body.close()
			return

		# creating a new response is better than removing all headers, etc. =)
		client.response = Response(status=500)
		client.done = True

		self._handle_exception(client, error)

	@handler("httperror_failure")
	def _on_httperror_failure(self, evt, error):
		client = evt.args[0]
		socket = client.socket
		try:
			state = self._buffers[socket]
		except KeyError:
			self._premature_client_disconnect(client)
			return
		if client in state.responses:
			return
		print('Exception in httperror_failure: %s, %r' % (error, client))
		self.default_internal_server_error(client, error)
		self.fire(write(socket, bytes(client.response)))
		self.fire(write(socket, bytes(client.response.headers)))
		self.fire(write(socket, bytes(client.response.body)))
		self.fire(close(socket))

	def default_internal_server_error(self, client, error):
		client.request = Request()
		client.response = Response(status=500)
		client.response.headers['Content-Length'] = str(len(client.response.body)).encode('ASCII')
		return HTTPError(client, INTERNAL_SERVER_ERROR())

	@handler("exception")
	def _on_exception(self, *args, **kwargs):
		fevent = kwargs['fevent']
		if fevent.name == '_read':
			socket = fevent.args[0]
			self.fire(close(socket))
		elif isinstance(fevent, (read, RequestEvent, ResponseEvent, HTTPError)):
			pass  # already handled
		elif fevent.name == 'response.body':
			socket = fevent.args[0].socket
			self.fire(close(socket))
		elif fevent.name == 'httperror_success':
			self._on_httperror_failure(fevent.args[0], args)
		else:
			# TODO: log
			handler = reprhandler(kwargs['handler']) if kwargs['handler'] else 'Unknown'
			print('Exception in %s\nTraceback: %s' % (handler, ''.join(args[2])))

	@handler("disconnect", "close")
	def _on_disconnect_or_close(self, socket=None):
		if not socket:
			# server socket was closed
			return
		socket.close()
		self._remove_client(socket)

	def _remove_client(self, socket):
		if socket in self._buffers:
			del self._buffers[socket]

	def _premature_client_disconnect(self, client):
		request, response = client
		# security: make sure that the generator is executed
		if response.body.generator and not request.method.safe:
			bytes(response.body)
		response.body.close()

	def _handle_exception(self, client, error):
		etype, httperror, traceback = error
		if not isinstance(httperror, StatusException):
			httperror = INTERNAL_SERVER_ERROR(u'%s (%s)' % (etype.__name__, httperror))
		if not isinstance(traceback, (list, tuple)):
			traceback = format_tb(traceback)
		httperror.traceback = u''.join(traceback + format_exception_only(*error[:2]))
		# channels = set([c.channel for c in (self, client.server, client.domain, client.resource) if c is not None])
		channels = [self.channel]
		self.fire(HTTPError(client, httperror), *channels)

	@handler('error')
	def _on_socket_error(self, socket, error):
		print('SocketError: %r: %s' % (socket, error))
		if isinstance(error, SSLError):
			if error.errno == 1 and getattr(error, 'reason', None) == 'HTTP_REQUEST' or error.strerror.endswith(':http request'):
				self.http_through_ssl(socket)
				return
			self.fire(close(socket))

	def http_through_ssl(self, socket):
		# If we receive a plain HTTP request and we're a TLS enabled socket
		# inform the user about his misusage and close the connection immediately.
		self.fire(write(socket, b"""Your browser sent a request that this server could not understand.
Reason: You're speaking plain HTTP to an SSL-enabled server port.
Instead use the HTTPS scheme to access this URL, please: https://%s"""))  # TODO: add URI by parsing the data which were written into the socket
		self.fire(close(socket))

	def ssl_through_http(self, socket):
		# If we receive a SSL handshake at the start of a request
		# and we're not a secure server, then immediately close the
		# client connection since we can't respond to it anyway.
		parser = self._buffers[socket].parser.parse

		def parse(data):
			# TODO: if we have a socket with TLS support we should try to use it instead so that we can speak HTTPS and redirect to the other port.
			# self.fire(write(socket, b'\x15\x03\x01\x00\x02\x02('))
			self.fire(write(socket, b'\x15\x03\x01\x00\x02\x02G'))
			# self.fire(write(socket, b'<html><head><title>use plaintext HTTP</title></head><body></body>USE HTTP!</html>'))
			self.fire(close(socket))
			return parser(b'')
		self._buffers[socket].parser.parse = parse
