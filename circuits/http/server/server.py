# -*- coding: utf-8 -*-
"""HTTP server"""

from __future__ import absolute_import
from __future__ import unicode_literals

from types import GeneratorType

from circuits import BaseComponent, handler
from circuits.net.utils import is_ssl_handshake
from circuits.net.events import close, write, read
from circuits.http.wrapper import Client, Server
from circuits.http.events import HTTPError, request as RequestEvent, response as ResponseEvent, stream

from httoop import HTTPStatusException, INTERNAL_SERVER_ERROR, Response
from httoop.server import ServerStateMachine, ServerPipeline


class HTTP(BaseComponent):
	"""HTTP Server Protocol Component

		Parse incoming HTTP messages and send a response message.
	"""

	channel = 'http'

	def __init__(self, channel=channel):
		super(HTTP, self).__init__(channel=channel)
		self._buffers = {}
		self._pipelines = {}
		self._response_to_client = {}

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

			self._buffers[socket] = ServerStateMachine(server.scheme, server.host, server.port)
			self._pipelines[socket] = ServerPipeline()

		http = self._buffers[socket]

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
		self._pipelines[socket] + tuple(client)
		self._response_to_client[response] = client
		return client

	@handler("response")
	def _on_response(self, client):
		"""Send respond message to client's socket"""

		request, response = client
		headers = response.headers
		socket = client.socket

		try:
			self._buffers[socket]
		except KeyError:  # client disconnected before getting answer
			self._premature_client_disconnect(client)
			return

		pipeline = self._pipelines[socket]
		if not pipeline.ready(response):
			return  # a previous request is unfinished

		# send HTTP response status line and headers
		bresponse = bytes(response)
		bheaders = bytes(headers)

		self.fire(write(socket, b'%s%s' % (bresponse, bheaders)))
		yield self.fire(stream(client))

	@handler("stream")
	def _on_stream(self, client):
		"""stream the response output"""

		request, response = client
		socket = client.socket

		try:
			data = next(response.body)
		except StopIteration:
			response.body.close()
			#if response.close:
			#	self.fire(close(socket))
			client.done = True
		else:
			self.fire(write(socket, data))
			yield self.fire(stream(client))

	@handler('stream_complete')
	def _on_stream_finished(self, evt, value):
		client = evt.args[0]
		socket = client.socket
		self._response_to_client.pop(client.response, None)
		try:
			pipeline = self._pipelines[socket]
		except KeyError:  # client disconnected
			self._premature_client_disconnect(client)
			return
		try:
			response = next(pipeline)
		except StopIteration:  # no more requests in the pipeline
			if pipeline.close:
				self.fire(close(socket))
		else:
			self.fire(ResponseEvent(self._response_to_client[response]))

	@handler("httperror_success")
	def _on_httperror(self, client, httperror):
		"""default HTTP error handler"""
		client, httperror = client.args
		# TODO: move into httoop?
		# set the corresponding HTTP status
		client.response.status = httperror.status

		# set HTTP headers
		client.response.headers.update(httperror.headers)

		# set HTTP Body
		client.response.body = httperror.body

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

		# FIXME: remove, it may breaks pipelining
		# creating a new response is better than removing all headers, etc. =)
		client.response = Response(status=500)
		self._response_to_client[client.response] = client
		client.done = True

		self._handle_exception(client, error)

	@handler("httperror_failure", "httperror_success_failure")
	def _on_httperror_failure(self, evt, error):
		# TODO: log
		# FIXME: success_failure will fail, due to argument
		client = evt.args[0]
		socket = client.socket
		self.fire(write(socket, b'%s\r\n' % (Response(status=500),))) # TODO: self.default_internal_server_error
		self.fire(close(socket))

	@handler("error")
	def _on_error(self, etype, evalue, traceback, handler=None, fevent=None):
		if isinstance(fevent, read):
			socket = fevent.args[0]
			self.fire(close(socket))
		elif isinstance(fevent, (RequestEvent, ResponseEvent, HTTPError)):
			pass # already handled
		elif isinstance(fevent, stream):
			socket = fevent.args[0].socket
			self.fire(close(socket))
		else:
			# TODO: log
			# print '## handler=', repr(handler), '## fevent=', repr(fevent)
			pass

	@handler("disconnect", "close")
	def _on_disconnect_or_close(self, socket=None):
		if not socket:
			# server socket was closed
			return
		self._remove_client(socket)

	def _remove_client(self, socket):
		if socket in self._buffers:
			del self._buffers[socket]
		if socket in self._pipelines:
			del self._pipelines[socket]

	def _premature_client_disconnect(self, client):
		request, response = client
		# security: make sure that the generator is executed
		if isinstance(response.body.content, GeneratorType) and not request.method.safe:
			bytes(response.body)
		response.body.close()
		self._response_to_client.pop(response, None)

	def _handle_exception(self, client, error):
		etype, httperror, traceback = error
		if not isinstance(httperror, HTTPStatusException):
			httperror = INTERNAL_SERVER_ERROR('%s (%s)' % (etype.__name__, httperror))
		httperror.traceback = traceback
		self.fire(HTTPError(client, httperror))
