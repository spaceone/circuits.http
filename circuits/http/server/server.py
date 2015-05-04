# -*- coding: utf-8 -*-
"""HTTP server"""

from __future__ import absolute_import
from __future__ import unicode_literals

from types import GeneratorType

from circuits import BaseComponent, handler
from circuits.net.utils import is_ssl_handshake
from circuits.net.events import close, write
from circuits.http.wrapper import Client, Server
from circuits.http.events import HTTPError, request as RequestEvent, response as ResponseEvent, stream

from httoop import HTTPStatusException
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
