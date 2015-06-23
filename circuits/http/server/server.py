# -*- coding: utf-8 -*-
"""HTTP server"""

from __future__ import absolute_import
from __future__ import unicode_literals

from ssl import SSLError
from time import time
from traceback import format_tb

from circuits import BaseComponent, handler, reprhandler, Event
from circuits.net.utils import is_ssl_handshake
from circuits.net.events import close, write, read
from circuits.http.wrapper import Client, Server
from circuits.http.events import HTTPError, request as RequestEvent, response as ResponseEvent

from httoop import HTTPStatusException, INTERNAL_SERVER_ERROR, Response
from httoop.server import ServerStateMachine
from httoop.semantic.response import ComposedResponse

_ResponseStart = type(b'response.start', (Event,), {})
_ResponseBody = type(b'response.body', (Event,), {})
_ResponseComplete = type(b'response.complete', (Event,), {})


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
			if not server.secure and is_ssl_handshake(data):
				# If we receive an SSL handshake at the start of a request
				# and we're not a secure server, then immediately close the
				# client connection since we can't respond to it anyway.
				self.fire(close(socket))
				return

			self._buffers[socket] = {
				'parser': ServerStateMachine(server.scheme, server.host, server.port),
				'requests': [],
				'responses': set(),
				'response_started': set(),
				'timeout': None,
				'composed': {}
			}

		http = self._buffers[socket]['parser']

		try:
			requests = tuple(http.parse(data))
		except HTTPStatusException as httperror:
			client = self._add_client(http.request, http.response, socket, server)
			self.fire(HTTPError(client, httperror))
			# TODO: wait for HTTPError event to be processed and close the connection
		else:
			for request, response in requests:
				client = self._add_client(request, response, socket, server)
				self.fire(RequestEvent(client))

	def _add_client(self, request, response, socket, server):
		client = Client(request, response, socket, server)
		self._buffers[socket]['requests'].append(client)
		return client

	@handler('read', 'connect', priority=-0.1)
	def _timeout(self, *args):
		self.fire(Event.create(b'timeout.check', args[0]))

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

		timeout = state['timeout']
		if timeout is not None:
			timeout.abort = True
			timeout.expiry = time()

		timeout = sleep(self.connection_idle_timeout)
		timeout.abort = False
		state['timeout'] = timeout

		yield timeout

		if timeout.abort:
			return
		if all(client.done for client in state['requests']):
			self.fire(close(socket))
		#else:
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

		if client in state['responses']:
			raise RuntimeError('Got multiple response events for client: %r' % (client,))

		state['responses'].add(client)
		pipeline = state['requests']
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

		state['response_started'].add(client)

		# prepare for sending
		composed = ComposedResponse(response, request)
		composed.prepare()
		state['composed'][client] = composed

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
			#if response.close:
			#	self.fire(close(socket))
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
		pipeline = state['requests']
		assert pipeline and pipeline[0] is client
		pipeline.pop(0)

		try:
			client_ = pipeline[0]
		except IndexError:  # no further request
			if state['composed'][client].close:  # FIXME: composed
				self.fire(close(socket))
		else:
			if client_ in state['responses'] and client_ not in state['response_started']:
				self.fire(_ResponseStart(client_))

	@handler('httperror')
	def _on_httperror(self, event, client, httperror):
		try:
			state = self._buffers[client.socket]
		except KeyError:
			self._premature_client_disconnect(client)
			return

		if client in state['responses']:
			event.stop()
			raise RuntimeError('Got httperror event after response event. Client: %r, HTTPError: %r. Ignoring it.' % (client, httperror))

	@handler("httperror_success")
	def _on_httperror_success(self, client, httperror):
		"""default HTTP error handler"""
		client, httperror = client.args
		# TODO: move into httoop?
		# set the corresponding HTTP status
		client.response.status = httperror.status

		# set HTTP headers
		client.response.headers.update(httperror.headers)

		# set HTTP Body
		client.response.body = httperror.body

		channels = set([c.channel for c in (self, client.server, client.domain, client.resource) if c is not None])
		event = Event.create(b'httperror_%d' % (httperror.status,))
		self.fire(event, *channels)
		yield self.wait(event)

		client.response.body.encode()

		self.fire(ResponseEvent(client))

	@handler("request_failure")
	def _on_request_failure(self, evt, error):
		"""Handler for exceptions occuring in the request or response event handler"""
		client = evt.args[0]

#		if client.redirected:
#			return
#		if isinstance(evalue, InternalRedirect):
#			client.request.uri = evalue.uri
#			client.redirected = True
#			self.fire(Request(client))
#			return

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

	@handler("httperror_failure", "httperror_success_failure")
	def _on_httperror_failure(self, evt, error):
		# TODO: log
		# FIXME: success_failure will fail, due to argument
		client = evt.args[0]
		socket = client.socket
		try:
			state = self._buffers[socket]
		except KeyError:
			self._premature_client_disconnect(client)
			return
		if client in state['responses']:
			return
		self.fire(write(socket, b'%s\r\n' % (Response(status=500),))) # TODO: self.default_internal_server_error
		self.fire(close(socket))
		print('Exception in httperror_failure: %s' % (error,))

	@handler("exception")
	def _on_exception(self, *args, **kwargs):
		fevent = kwargs['fevent']
		if isinstance(fevent, read):
			socket = fevent.args[0]
			self.fire(close(socket))
		elif isinstance(fevent, (RequestEvent, ResponseEvent, HTTPError)):
			pass # already handled
		elif fevent.name == 'response.body':
			socket = fevent.args[0].socket
			self.fire(close(socket))
		else:
			# TODO: log
			handler = reprhandler(kwargs['handler']) if kwargs['handler'] else 'Unknown'
			print('Exception in %s\nTraceback: %s' % (handler, ''.join(args[2])))

	@handler("disconnect", "close")
	def _on_disconnect_or_close(self, socket=None):
		if not socket:
			# server socket was closed
			return
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
		if not isinstance(httperror, HTTPStatusException):
			httperror = INTERNAL_SERVER_ERROR('%s (%s)' % (etype.__name__, httperror))
		httperror.traceback = format_tb(traceback)
		self.fire(HTTPError(client, httperror))

	@handler('error')
	def _on_socket_error(self, socket, error):
		if isinstance(error, SSLError):
			if error.errno == 1 and getattr(error, 'reason', None) == 'HTTP_REQUEST' or error.strerror.endswith(':http request'):
				self._plain_http_trough_ssl(socket)
			self.fire(close(socket))

	def _plain_http_trough_ssl(self, socket):
		self.fire(write(socket, """Your browser sent a request that this server could not understand.
Reason: You're speaking plain HTTP to an SSL-enabled server port.
Instead use the HTTPS scheme to access this URL, please: https://%s"""))  # TODO: add URI by parsing the data which were written into the socket
